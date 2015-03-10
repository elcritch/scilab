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
def matchfilename(testfolder, pattern, strictmatch=True):
    print(mdBlock("Matching pattern: `{}` in testfolder: `{}`, strictmatch: {} ", pattern, testfolder, strictmatch))
    files = sorted(testfolder.rglob(pattern))
    debug(files)
    if strictmatch:
        assertsingle(files)
    return files[-1]

# @debugger
def resolve(url):
    return Path(url).resolve()


def match_data_description(testfolder):
    
    ## temporary, later lookup test config
    project_description_url = Path(__file__).parent / "project_description.v1.json"    
    project_description = Json.load_json_from(project_description_url.resolve())
    
    return project_description


def process_raw_columns(data, raw_config):

    rawdata = data.file.data
    # debug(rawdata)
    
    csv_cols_index_full = { v.full: v for v in data.file.data.values() 
                                    if isinstance(v, InstronColumnData) }
    
    debug(list(csv_cols_index_full.keys()))
    
    output = []
    
    for rawcol in raw_config.columns:
        print(mdBlock("**Raw Column**: {}".format(repr(rawcol.info))))
        # debug([rawcol])
        
        if rawcol.info.full not in csv_cols_index_full:
            raise KeyError("Column Missing from Data: column: `{}` data file columns: `{}`".format(repr(rawcol.info.full), repr(csv_cols_index_full.keys())))
        
        output.append((rawcol.info, csv_cols_index_full[rawcol.info.full]))
    
    return output 

# @debugger
def normalize_columns(data, norm_config, filenames, state):
    
    # TODO: load 'raw' file (from matlab)
    # TODO: load 'info' data (need to update this first?)
    #            - need to save data into "flat excel file"
    
    # data = DataTree(data)
    shortdetails = DataTree(state.details)
    # testdetails.__dict__['_ignore'] = ['summaries']
    # debug(type(data))
    debug( flatten_type( data ) )
    debug( flatten_type( state ) )
    print('\n')
    
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
        
        # print(list( dir(normedinfo)), normedinfo._fieldnames)
        
        
        col.info = normedinfo.set(**col.get('info',{}))
        
        # if 'column' in col.source:
        #     key, sourcefunc = getpropertypair(col.source)
        #     # if key == 'column': # fix attribute accessors ...
        #     #     sourcefunc = sourcefunc.split('.')
        #     #     sourcefunc = sourcefunc[0] + ''.join([ "['%s']"%f for f in sourcefunc[1:]])
        #
        #     normeddata = executeexpr(sourcefunc, **env)
        # else:
        #     raise Exception("Unimplemented normalization source mode: "+str(col.source))
            
        if col['conversion','constant']:
            key, constantexpr = getpropertypair(col.conversion)
            constant_factor = executeexpr(constantexpr, details=state.details, )
            normeddata = normeddata * constant_factor
        
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
    
    raw_config, normalized_config = processor

    print(mdHeader(3, "Raw Data"))
    # ================================================
    
    output = DataTree()
    output['raw','files'] = getfilenames(testfolder, 
                                stage="raw", 
                                header=DataTree(item=state.methoditem.name), 
                                version=state.args.version, 
                                matlab=True)
    
    checkanyexists = lambda x: any(k for k,v in x.items() if not v.exists())
    if 'raw' in state.args['forces',] or not checkanyexists(output.raw.files.names):
        columnmapping = process_raw_columns(data, raw_config)

        indexes = ['step'] + raw_config.get('_slicecolumns_', []) 
        save_columns(columnmapping=columnmapping, indexes=indexes, filenames=output.raw.files)
    else:
        print("Skipping processing raw stage. File exists: `{}`".format(rawoutfiles.names.matlab))


    print(mdHeader(3, "Normalize Data"))
    # ================================================

    output['norm','files'] = getfilenames(testfolder, 
                                stage="norm", 
                                header=DataTree(item=state.methoditem.name), 
                                version=state.args.version, 
                                matlab=True)

    if 'norm' in state.args['forces',] or not checkanyexists(output.norm.files.names):
        rawdata = load_columns(output.raw.files.names, "matlab") 
        debug(type(rawdata), rawdata.keys())
        data = DataTree(raw=rawdata)
        columnmapping = normalize_columns(data, normalized_config, output.norm.files, state)
        indexes = ['step'] + normalized_config.get('_slicecolumns_', []) 
        save_columns(columnmapping=columnmapping, indexes=indexes, filenames=output.norm.files)
    else:
        print("Skipping processing norm stage. File exists: `{}`".format(rawoutfiles.names.matlab))


def process_method(methodname, method, testfolder, projdesc, state):
    
    files = DataTree()
    
    for methoditem in method:
        
        print(mdHeader(3, "Method Item: {} ".format(methoditem.name)))
        # ================================================
        debug(methoditem)
        
        
        testdetails = Json.load_json_from(testfolder.details)        
        state.details = testdetails
        # = Files =
        data = DataTree()        
        if 'files' in methoditem:
            debug(methoditem.files)
            data.file = getproperty(methoditem.files, action=True, 
                                    env=DataTree(details=state.details, testfolder=testfolder))        
        
        # ====================
        # = Handle Processor =
        # ====================
        processorname = methoditem.processor['$ref'].lstrip('#/processors/')
        print(mdHeader(4, "Processor: {}".format(processorname)))
        processor = projdesc.processors[processorname]

        itemstate = state.set(methoditem=methoditem, methodname=methodname)
        process(testfolder=testfolder, data=data, processor=processor, state=itemstate)

def process_methods(testfolder, state, args):
    
    projdesc = match_data_description(testfolder)
    state.projdesc = projdesc
    
    for methodprop in projdesc.methods:
        methodname, method = getpropertypair(methodprop)
        
        print(mdHeader(2, "Data Method: `{}` ".format(methodname)))
        process_method(methodname, method, testfolder, projdesc, state=state.set(methodname=methodname))
        
def run(testfolder, args):
    
    args.forces = DataTree(raw=True, norm=True)
    args.version = "0"
    state = DataTree()
    state.args = args
    process_methods(testfolder, state, args)


def main():
    
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
    
if __name__ == '__main__':
    main()
    
    