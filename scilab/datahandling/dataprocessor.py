#!/usr/bin/env python3

import os, sys, pathlib, re, logging
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
import scilab.datahandling.datasheetparser as datasheetparser  
import scilab.datahandling.processimagemeasurement as processimagemeasurement
import scilab.utilities.merge_calculated_jsons as merge_calculated_jsons
import scilab.expers.mechanical.fatigue.run_image_measure as run_image_measure

import numpy as np

import shutil
from tabulate import tabulate

# @debugger
def resolve(url):
    return Path(url).resolve()


def process_raw_columns(data, raw_config, state):

    # === Handle Raw Files === 
    handle_files(data, state.methoditem, state, state.testfolder)
    rawdata = data.file.data
    
    csv_cols_index_full = { v.full.strip(): v for v in data.file.data.values() 
                                    if isinstance(v, InstronColumnData) }
    
    debug(list(csv_cols_index_full.keys()))
    
    output = []
    
    for rawcol in raw_config.columns:
        print("<i>Raw Column:<i> {}".format(repr(rawcol.info)))        
        
        # ============================================================
        # = Handle Raw Columns with multiple possible row conditions =
        # ============================================================
        if rawcol.get('source', None):
            env = DataTree(details=state.details, **data)
            sourcecol = getproperty(rawcol.source, action=True, env=env)
            # fullsourcename = next([ o.full for o in output if o.name == sourcecol])
            # fulls.append(fullsourcename)
            if sourcecol[0].isspace():
                raise ValueError("Column Names cannot include spaces!", sourcecol, rawcol)
            debug(sourcecol, [ (rc.name, oc.name,rc.name==sourcecol, sourcecol) for rc,oc in output ])
            origcol = [ oc for rc,oc in output if rc.name == sourcecol ][0]
            output.append((rawcol.info, origcol))
        else:
            # otherwise process "full" name(s)
            fulls = rawcol.get('fulls',[])
            
            # first add any single names
            if rawcol.info.get('full', None):
                fulls.append(rawcol.info.full)
        
            # next check for 
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

def normalize_columns(data, norm_config, filenames, state):    
    output = []
    
    get_attr_to_item = lambda xs: ''.join([ "['%s']"%x for x in xs.split('.')])
    re_attribs = lambda k, s: re.sub(r"(%s)((?:\.\w+)+)"%k, lambda m: print(m.groups()) or m.groups()[0]+get_attr_to_item(m.groups()[1][1:]), s)
            
    # @debugger
    def _normalize(col):

        env = DataTree(details=state.details, **data)
        sourcecol = getproperty(col.source, action=True, env=env)

        if sourcecol:
            print(mdHeader(4, "Column: {}", sourcecol))
        
            normeddata = executeexpr("raw.data.{col}".format(col=sourcecol), **env)
            normedinfo = executeexpr("raw.columninfo.{col}".format(col=sourcecol), **env)
            normedinfo = DataTree( ((f,getattr(normedinfo,f)) for f in normedinfo._fieldnames) )    
            col.info = normedinfo.set(**col.get('info',{}))
        else:
            normeddata = None
        
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
        # debug(normedcoldata)
        print("Normed data name:{} shape:{}".format(col.info.label, normedcoldata.shape))
        print()
        
        normcol = DataTree(array=normedcoldata, summary=summaryvalues(normedcoldata, np.s_[0:-1]))
        output.append( [ col.info, normcol ] )
        data['norm',col.info.name] = normcol.array
    
    return output 

    
def process_variables(testfolder, state, name, kind:"pre|post", data):
    print("### Processing Variables ")
    
    variables_input = state['methoditem','variables', name, kind]
    
    if not variables_input: 
        variables = DataTree()
    else:
        env = DataTree(details=state.details, codehandlers=state.args.codehandlers, **data )
        variables = getproperty(variables_input, action=True, env=env)

    state.variables = variables

    vardict = DataTree()
    vardict[ tuple( i[1] for i in state.position )+(name, kind, ) ] = variables
    # debug(vardict)
    # print(vardict)
    
    jsonpath, allvariables = testfolder.save_calculated_json(
        test=state.args.testconf, 
        name="variables", 
        data=vardict,
        # mergeschema={"properties": {'m3_cycles': {'tracking': {'norm': {'post': {"mergeStrategy": "overwrite"} }}}, 'tracking': {"mergeStrategy": "overwrite"} } },
        )
    
    state.variables.update( allvariables["variables"] )
    # debug(allvariables, state.variables)
    
    return 
    
    
def process(testfolder, data, processor, state):    
    try:
        raw_config, normalized_config = processor
        default_index = [{"column":'step',"type":"int"},]
        save_config = DataTree(projdesc=json.dumps(state.projdesc))
        header=OrderedDict(method=state.methodname, item=state.methoditem.name)
        def missingFiles(x): 
            missing = [ k for k,v in x.items() if not v.exists() ]
            debug(missing)
            return missing
    
        forceRuns = state.args.get('forceRuns',DataTree())
        debug(forceRuns)
        
        # varfilename = "{methodname}.{methoditem.name}.calculated".format(**state)
        # testfolder.save_calculated_json(test=state.args.testconf, name="variables", data={}, overwrite=True)
        
        # ====================
        # = Process Raw Data =
        # ====================
        print(mdHeader(3, "Raw Data"))
    
        output = DataTree()
        output['raw','files'] = getfilenames(
            test=state.args.testconf, testfolder=testfolder, stage="raw", 
            version=state.args.version, header=header, matlab=True, excel=state.args.excel)
    
        
        print("Checking Raw files: forceRuns:`{}`, missing output:`{}`".format(
                forceRuns['raw',], missingFiles(output.raw.files.names)))
        
        if forceRuns['raw',] or missingFiles(output.raw.files.names):
            if not state.args['onlyVars',]:
                missingFiles(output.raw.files.names)
                columnmapping = process_raw_columns(data, raw_config, state)
                indexes = default_index + raw_config.get('_slicecolumns_', [])
                save_columns(columnmapping=columnmapping, indexes=indexes, configuration=save_config, filenames=output.raw.files)
            else:
                print("Skipping saving `raw` columns. Only updating variable json. ")
        else:
            print("Skipping processing `raw` stage. Files exists: `{}`".format(output.raw.files.names))

        # =====================
        # = Process Norm Data =
        # =====================
        print(mdHeader(3, "Normalize Data"))

        output['norm','files'] = getfilenames(
            test=state.args.testconf, testfolder=testfolder, stage="norm", 
            version=state.args.version, header=header, matlab=True, excel=state.args.excel)
        
        print("Checking Norm files: forceRuns:`{}`, missing output:`{}`".format(
                forceRuns['norm',], missingFiles(output.norm.files.names)))
        
        if forceRuns['norm',] or missingFiles(output.norm.files.names):
            
            normstate = state.set(processorname=normalized_config.name)
            
            rawdata = load_columns(output.raw.files.names, "matlab")
            
            data = DataTree(raw=rawdata)
            
            # ======   Save Pre Variables  ====== #
            process_variables(testfolder, normstate, normalized_config.name, "pre", data)

            # ====== Normalize Columns ====== #
            columnmapping = normalize_columns(data, normalized_config, output.norm.files, normstate)
            indexes = [{"column":'step',"type":"int"}] + normalized_config.get('_slicecolumns_', [])
            
            # ======   Save Post Variables  ====== #
            normdata = columnmapping_vars(columnmapping)
            data.norm = DataTree(**columnmapping_vars(columnmapping))
            process_variables(testfolder, state, normalized_config.name, "post", data)
                        
            if not state.args['onlyVars',]:
                save_columns(columnmapping=columnmapping, indexes=indexes, configuration=save_config, filenames=output.norm.files)
            else:
                print("Skipping saving `norm` columns. Only updating variable json. ")
        else:
            print("Skipping processing `norm` stage. File exists: `{}`".format(output.norm.files.names))
            
            
            
    except Exception as err:
        # debughere()
        raise err



def handle_files(data, methoditem, state, testfolder):
    
    if 'files' in methoditem:
        
        print("### Handle Raw Files")
        env = DataTree(details=state.details, testfolder=testfolder, projectfolder=state.filestructure)
        # import json
        # print(json.dumps(env, cls=CustomDebugJsonEncoder))

        try:
            filetype, filevalue = getpropertypair(methoditem.files)
            debug(filevalue)
            
            filename = safefmt(getproperty(filevalue, action=True, errorcheck=False, env=env),**env)
            debug(filename)
            filepath = matchfilename(filename, strictmatch=False)
            debug(filepath)
        except Exception as err:
            # logging.error("Error looking up file: ", err)
            raise Exception("Cannot find file for ", err, ['optional'])
            # raise ProcessorException("Cannot find file for pattern: {} in method: {}".format(filevalue, methoditem.name), err)
        
        if filepath and filepath.exists():
            data.file = getproperty(DataTree(_csv_=filepath), action=True, env=env)
        else:
            # print(debugger_summary("handle_files", state, ignores=['filestructure.projdesc','args', 'details']))
            # print(debugger_summary("handle_files:locals", locals(), ignores=['builtins', 'state', 'data', 'methoditem'] ))
            # if filenameerr:
            #     raise Exception("format exception:",filevalue, filenameerr)
            
            # raise ProcessorException("Cannot find file for pattern: {} in method: {}".format(filevalue, methoditem.name), err )
            raise ProcessorException("Cannot find file for pattern: {} in method: {}".format(filevalue, methoditem.name),['optional'])



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
            
        # ====================
        # = Handle Processor =
        # ====================
        processorname = methoditem.processor['$ref'].lstrip('#/processors/')
        print(mdHeader(4, "Processor: {}".format(processorname)))
        processor = projdesc.processors[processorname]

        itemstate = state.set(methoditem=methoditem, methodname=methodname)
        push(itemstate, 'methoditem',methoditem.name)        
        debug(itemstate.position)
        itemstate.testfolder = testfolder
        process(testfolder=testfolder, data=data, processor=processor, state=itemstate)


def process_methods(testfolder, state, args):

    # debug(state.filestructure.projdesc)
    
    projdesc = state.filestructure.projdesc
    state.projdesc = projdesc
    
    for methodprop in projdesc.methods:
        try:
            methodname, method = getpropertypair(methodprop)
        
            print(mdHeader(2, "Data Method: `{}` ".format(methodname)))
            substate = state.set(methodname=methodname, method=method)
            push(substate, 'methodname',methodname)
            process_method(methodname, method, testfolder, projdesc, state=substate)
        except Exception as err:
            print("type:",str(type(err.args[-1])).replace('<','≤'))
            if isinstance(err.args[-1],(tuple,list)) and 'optional' in err.args[-1]:
                continue
            else:
                raise err
        
def run(filestructure, testfolder, args):
    
    # ==================
    # = Set Arguements =
    # ==================
    
    state = DataTree()
    state.args = args
    state.filestructure = filestructure
    state.position = []
    
    # push(state, 'testinfo', args.testconf.info.short)
    # push(state,  'testfolder', testfolder)
    


print("Run normalize_instron_data")



# ====================
# = Script Execution =
# ====================

def display(*args, **kwargs):
    print(*args, **kwargs)

def HTML(arg, whitespace=None):
    if whitespace:
        return "<div style='white-space: {whitespace};'>\n{ret}\n</div>\n".format(whitespace=whitespace, ret=arg)
    else:
        ret = arg.replace('\n','\r')
        return ret

def execute(fs, name, testconf, args):
    
    print("\n")
    display(HTML("<h2>Processing Test: {} | {}</h2>".format(testconf.info.short, name)))
    
    folder = fs.testfolder(testinfo=testconf.info)
    
    # try:
    os.symlink(str(folder.testdir), str(fs.processed / testconf.info.short ), target_is_directory=True )
    
    data = [ (k,v.relative_to(args.parentdir), "&#10003;" if v.exists() else "<em>&#10008;</em>" ) 
                for k,v in flatten(folder).items() if v ]
    data = sorted(data)

    print()
    print(HTML(tabulate( data, [ "Name", "Folder", "Exists" ], tablefmt ='pipe' ), whitespace="pre-wrap"))
    debug(folder.data.relative_to(args.parentdir))
    
    args.testname = name
    args.testconf = testconf
    args.report = sys.stdout
    
    testconf.folder = folder
    
    # Setup Arguments Environment
    state = DataTree()
    state.args = args
    state.filestructure = fs
    state.position = []
    
    # update json details
    print(mdHeader(2, "Run Image Measurement"))
    
    imageconfstate = state.set(image_measurement=fs.projdesc["experiment_config","config","calibration","image_measurement"])
    processimagemeasurement.process_test(testconf, state=imageconfstate, args=args)
    # run_image_measure.process_test(testconf.info, testconf.folder)
    
    print(mdHeader(2, "Make JSON Data"))
    
    datasheetparser.handler(testconf=testconf, excelfile=folder.datasheet, args=args)
    merge_calculated_jsons.handler(testinfo=testconf.info, testfolder=testconf.folder, args=args, savePrevious=True)
    
    print(mdHeader(2, "Executing"))
    
    process_methods(folder, state, args)

    
    print(mdHeader(2, "Merging JSON Data"))
    merge_calculated_jsons.handler(testinfo=testconf.info, testfolder=testconf.folder, args=args, savePrevious=True)


def test_folder(args):
    
    import scilab.expers.configuration as config
    import scilab.expers.mechanical.fatigue.uts as exper
    # import scilab.expers.mechanical.fatigue.cycles as exper
    
    args.parser_data_sheet_excel = exper.parser_data_sheet_excel
    args.parser_image_measurements = exper.parser_image_measurements
    args.codehandlers = exper.getcodehandlers()
    
    # parentdir = Path(os.path.expanduser("~/proj/expers/")) / "fatigue-failure|uts|expr1"
    # parentdir = Path(os.path.expanduser("~/proj/expers/")) / "exper|fatigue-failure|cycles|trial1"
    args.parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper|fatigue-failure|cycles|trial1"
    # args.parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper|fatigue-failure|uts|trial1"
    # args.parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper|fatigue-failure|uts|trial3"
    
    pdp = args.parentdir / 'projdesc.json' 
    print(pdp)
    # print(pdp.resolve())
    
    fs = config.FileStructure(projdescpath=pdp, verify=True, project=args.parentdir)
    # Test test images for now
    test_dir = fs.tests.resolve()
    testitemsd = fs.testitemsd()

    testitems = { k.name: DataTree(info=k, folder=v, data=DataTree() ) for k,v in testitemsd.items()}
    
    summaries = OrderedDict()
    
    for name, testconf in sorted( testitems.items() )[:]:
        # if name != "jan13(gf10.2-rlm)-wa-tr-l6-x3":
        # if 'tr' not in name or name < "nov24(gf9.2-llm)-wa-tr-l5-x2":
        # if name < "jan14":
            # continue
        # if name not in ["jan14(gf10.2-rlm)-wa-lg-l9-x2",]:
            # continue
        
        try:
            execute(fs, name, testconf, args, )
            summaries[name] = "Success", ""
        except Exception as err:
            logging.error(err)
            summaries[name] = "Failed", str(err)
            raise err
        
    print("Summaries:\n\n")
    print(HTML(tabulate( [ (k,)+v for k,v in summaries.items()], [ "Test Name", "Status", "Error" ], tablefmt ='pipe' ), whitespace="pre-wrap"))
    print()

def main():
    # test_run()
    args = DataTree()
    # args.forceRuns = DataTree(raw=False, norm=True)
    args.version = "0"
    # args["force", "imagecropping"] = True
    # args["dbg","image_measurement"] = True
    # === Excel === 
    args.excel = False
    # args.excel = True
    # === Only Update Variables === 
    # args.onlyVars = False
    args.onlyVars = True
    
    
    test_folder(args)
    
if __name__ == '__main__':
    main()    

def test_run():
    
    samplefiles = Path(__file__).parent.resolve()/'..'/'..'/'test/instron-test-files'
    samplefiles = samplefiles.resolve()
    debug(samplefiles)
    
    ## create fake folder structure 
    testfolder = DataTree()
    testfolder['data'] = samplefiles / 'data' 
    testfolder['details'] = samplefiles / 'data' / 'instron-testconf.details.json'
    testfolder['datacalc'] = samplefiles / 'data' / 'processed' 
    testfolder['raw','csv','instron_test','tracking'] = samplefiles / 'instron-test-file.steps.tracking.csv' 
    testfolder['raw','csv','instron_test','trends'] = samplefiles / 'instron-test-file.steps.trends.csv' 
    
    args = DataTree()
    run(testfolder, args)

