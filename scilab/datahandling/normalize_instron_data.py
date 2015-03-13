#!/usr/bin/env python3

import os, sys, pathlib, re
import pandas as pd
import numpy as np
import scipy.io as sio
from pandas import ExcelWriter

import scilab.tools.jsonutils as Json
from scilab.tools.project import *
from scilab.expers.configuration import *
from scilab.tools.instroncsv import *

from scilab.datahandling.datahandlers import *
import scilab.datahandling.columnhandlers as columnhandlers  

import numpy as np

# @debugger
def resolve(url):
    return Path(url).resolve()


def process_raw_columns(data, raw_config):

    rawdata = data.file.data
    # debug(rawdata)
    
    csv_cols_index_full = { v.full: v for v in data.file.data.values() 
                                    if isinstance(v, InstronColumnData) }
    
    debug(list(csv_cols_index_full.keys()))
    
    output = []
    
    for rawcol in raw_config.columns:
        print(mdBlock("**Raw Column**: {}".format(repr(rawcol.info))))
        
        
        fulls = rawcol.get('fulls',[])
        if rawcol.info.get('full', None):
            fulls.append(rawcol.info.full)
        
        for full in fulls:
            rawcol.info.full = full
            if full in csv_cols_index_full:
                break
        
        if full not in csv_cols_index_full:
            debughere()
            cols = ''.join(map("<li>{}</li>".format, csv_cols_index_full.keys()))
            msg = "Column Missing from Data: column: `{}` data file columns: \n<ul>{}</ul>".format(
                repr(rawcol.info.full), cols)
            print(msg)
            raise KeyError(msg)        
        
        output.append((rawcol.info, csv_cols_index_full[full]))
    
    return output 

# @debugger
def normalize_columns(data, norm_config, filenames, state):    
    output = []
    
    get_attr_to_item = lambda xs: ''.join([ "['%s']"%x for x in xs.split('.')])
    re_attribs = lambda k, s: re.sub(r"(%s)((?:\.\w+)+)"%k, lambda m: print(m.groups()) or m.groups()[0]+get_attr_to_item(m.groups()[1][1:]), s)
            
    # @debugger
    def _normalize(col):

        env = DataTree(details=state.details, **data)
        sourcecol = getproperty(col.source, action=True, env=env)

        print(mdHeader(4, "Column: {}", sourcecol))
        
        normeddata = executeexpr("raw.data.{col}".format(col=sourcecol), **env)
        normedinfo = executeexpr("raw.columninfo.{col}".format(col=sourcecol), **env)
        normedinfo = DataTree( ((f,getattr(normedinfo,f)) for f in normedinfo._fieldnames) )
                
        col.info = normedinfo.set(**col.get('info',{}))
        if col['conversion','constant']:
            key, constantexpr = getpropertypair(col.conversion)
            constant_factor = executeexpr(constantexpr, details=state.details, data=data, variables=state.get('variables',DataTree()))
            debug(constant_factor)
            normeddata = normeddata * constant_factor
        if col['conversion','func']:
            key, constantexpr = getpropertypair(col.conversion)
            normeddata = executeexpr(constantexpr, x=normeddata, details=state.details, data=data, variables=state.get('variables',DataTree()))
            
        
        return normeddata
    
    # ====================================================
    # = Process Normalized Columns (one column per item) =
    # ====================================================
    for col in norm_config.columns:
        normedcoldata = _normalize(col)
        debug(normedcoldata)
        print("Normed data name:{} shape:{}".format(col.info.label, normedcoldata.shape))
        print()
        
        normcol = DataTree(array=normedcoldata, summary=summaryvalues(normedcoldata, np.s_[0:-1]))
        output.append( [ col.info, normcol ] )
    
    return output 
    
def process(testfolder, data, processor, state):
    
    try:
        raw_config, normalized_config = processor
        default_index = [{"column":'step',"type":"int"},]
        save_config = DataTree(projdesc=json.dumps(state.projdesc))
        header=OrderedDict(method=state.methodname, item=state.methoditem.name)
    
        print(mdHeader(3, "Raw Data"))
        # ================================================
    
        output = DataTree()
        output['raw','files'] = getfilenames(
            test=state.args.testinfo, testfolder=testfolder, stage="raw", 
            version=state.args.version, header=header, matlab=True, excel=state.args.excel)
    
        checkanyexists = lambda x: any(k for k,v in x.items() if not v.exists())
        if 'raw' in state.args['forces',] or not checkanyexists(output.raw.files.names):
            columnmapping = process_raw_columns(data, raw_config)

            indexes = default_index + raw_config.get('_slicecolumns_', []) 
            save_columns(columnmapping=columnmapping, indexes=indexes, configuration=save_config, filenames=output.raw.files)
        else:
            print("Skipping processing raw stage. File exists: `{}`".format(rawoutfiles.names.matlab))

        print(mdHeader(3, "Normalize Data"))
        # ================================================

        output['norm','files'] = getfilenames(
            test=state.args.testinfo, testfolder=testfolder, stage="norm", 
            version=state.args.version, header=header, matlab=True, excel=state.args.excel)

        if 'norm' in state.args['forces',] or not checkanyexists(output.norm.files.names):
            rawdata = load_columns(output.raw.files.names, "matlab") 

            data = DataTree(raw=rawdata)
        
            if state['methoditem','variables',normalized_config.name]:
                variables_input = state.methoditem.variables[normalized_config.name]
                variables = getproperty(variables_input, action=True, 
                                        env=DataTree(details=state.details, testfolder=testfolder, **data))
            
                debug(variables_input, variables)
                state = state.set(variables=variables)
                save_config.variables = variables

            columnmapping = normalize_columns(data, normalized_config, output.norm.files, state)
            indexes = [{"column":'step',"type":"int"}] + normalized_config.get('_slicecolumns_', [])
            save_columns(columnmapping=columnmapping, indexes=indexes, configuration=save_config, filenames=output.norm.files)
        else:
            print("Skipping processing norm stage. File exists: `{}`".format(rawoutfiles.names.matlab))
    except Exception as err:
        # debughere()
        raise err

def handle_files(data, methoditem, state, testfolder):
    
    if 'files' in methoditem:
        
        print("\nHandle")
        env = DataTree(details=state.details, testfolder=testfolder, projectfolder=state.filestructure)

        # try:
        filetype, filevalue = getpropertypair(methoditem.files)
        debug(filevalue)
        filename = safefmt(filevalue,**env)
        debug(filename)
        filepath = matchfilename(filename, strictmatch=False)
        debug(filepath)
        
        if filepath and filepath.exists():
            data.file = getproperty(DataTree(_csv_=filepath), action=True, env=env)
        else:
            # print(debugger_summary("handle_files", state, ignores=['filestructure.projdesc','args', 'details']))
            # print(debugger_summary("handle_files:locals", locals(), ignores=['builtins', 'state', 'data', 'methoditem'] ))
            # if filenameerr:
            #     raise Exception("format exception:",filevalue, filenameerr)
            
            raise ProcessorException("Cannot find file for pattern: {} in method: {}".format(filevalue, methoditem.name))

    

def process_method(methodname, method, testfolder, projdesc, state):
    
    files = DataTree()
    
    for methoditem in method:
        
        print(mdHeader(3, "Method Item: {} ".format(methoditem.name)))
        # ================================================
        debug(methoditem)
        
        
        testdetails = Json.load_json_from(testfolder.details)        
        state.details = testdetails
        state.methoditem = methoditem
        # = Files =
        data = DataTree()        
        handle_files(data, methoditem, state, testfolder)
            
        # ====================
        # = Handle Processor =
        # ====================
        processorname = methoditem.processor['$ref'].lstrip('#/processors/')
        print(mdHeader(4, "Processor: {}".format(processorname)))
        processor = projdesc.processors[processorname]

        itemstate = state.set(methoditem=methoditem, methodname=methodname)
        process(testfolder=testfolder, data=data, processor=processor, state=itemstate)

def process_methods(testfolder, state, args):

    # debug(state.filestructure.projdesc)
    
    projdesc = state.filestructure.projdesc
    state.projdesc = projdesc
    
    for methodprop in projdesc.methods:
        methodname, method = getpropertypair(methodprop)
        
        print(mdHeader(2, "Data Method: `{}` ".format(methodname)))
        process_method(methodname, method, testfolder, projdesc, state=state.set(methodname=methodname))
        
def run(filestructure, testfolder, args):
    
    args.forces = DataTree(raw=True, norm=True)
    args.version = "0"
    args.excel = True 
    
    state = DataTree()
    state.args = args
    state.filestructure = filestructure
    process_methods(testfolder, state, args)


print("Run normalize_instron_data")


def test_run():
    
    samplefiles = Path(__file__).parent.resolve()/'..'/'..'/'test/instron-test-files'
    samplefiles = samplefiles.resolve()
    debug(samplefiles)
    
    ## create fake folder structure 
    testfolder = DataTree()
    testfolder['data'] = samplefiles / 'data' 
    testfolder['details'] = samplefiles / 'data' / 'instron-test.details.json'
    testfolder['datacalc'] = samplefiles / 'data' / 'processed' 
    testfolder['raw','csv','instron_test','tracking'] = samplefiles / 'instron-test-file.steps.tracking.csv' 
    testfolder['raw','csv','instron_test','trends'] = samplefiles / 'instron-test-file.steps.trends.csv' 

    args = DataTree()
    run(testfolder, args)
    
def test_folder():
    
    import scilab.expers.configuration as config
    import scilab.expers.mechanical.fatigue.uts as exper_uts
    
    parentdir = Path(os.path.expanduser("~/proj/expers/")) / "fatigue-failure|uts|expr1"
    
    pdp = parentdir / 'projdesc.json' 
    print(pdp)
    print(pdp.resolve())
    
    fs = config.FileStructure(projdescpath=pdp,testinfo=exper_uts.TestInfo, verify=True)
    # Test test images for now
    test_dir = fs.tests.resolve()
    testitemsd = fs.testitemsd()
    
    import shutil
    from tabulate import tabulate

    testitems = { k.name: DataTree(info=k, folder=v, data=DataTree() ) for k,v in testitemsd.items()}

    def display(*args, **kwargs):
        print(*args, **kwargs)
    
    def HTML(arg):
        return arg
    
    args = DataTree()
    
    
    for name, test in sorted( testitems.items() )[:]:
        # if name not in ['dec09(gf10.1-llm)-wa-tr-l8-x1']:
        #     continue
        
        print("\n")
        display(HTML("<h2>{} | {}</h2>".format(test.info.short(), name)))
    
        folder = fs.testfolder(testinfo=test.info)
    
    #     debug(mapd(flatten(folder), valuef=lambda x: type(x), keyf=lambda x: x))
        
        data = [ (k,v.relative_to(parentdir), "&#10003;" if v.exists() else "<em>&#10008;</em>" ) 
                    for k,v in flatten(folder).items() ]
        data = sorted(data)
    
        display(HTML(tabulate( data, [ "Name", "Folder", "Exists" ], tablefmt ='html' )))
        debug(folder.data.relative_to(parentdir))
        
        args.testname = name
        args.testinfo = test
    
        run(fs, folder, args)
    
    

def main():
    
    # test_run()
    
    test_folder()
    
if __name__ == '__main__':
    main()
    
    