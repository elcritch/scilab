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
        print(mdBlock("**Raw Column**: {}".format(repr(rawcol))))
        # debug([rawcol])
        
        if rawcol.full not in csv_cols_index_full:
            raise KeyError("Column Missing from Data: column: `{}` data file columns: `{}`".format(repr(rawcol.full), repr(csv_cols_index_full.keys())))
        
        output.append((rawcol, csv_cols_index_full[rawcol.full]))
    
    return output 

# @debugger
def normalize_columns(testdetails, data, norm_config, filenames):
    
    # TODO: load 'raw' file (from matlab)
    # TODO: load 'info' data (need to update this first?)
    #            - need to save data into "flat excel file"
    
    # data = DataTree(data)
    shortdetails = DataTree(testdetails)
    testdetails.__dict__['_ignore'] = ['summaries']
    debug(type(data))
    debug(data.keys())
    print('\n')
    
    output = []
    
    get_attr_to_item = lambda xs: ''.join([ "['%s']"%x for x in xs.split('.')])
    re_attribs = lambda k, s: re.sub(r"(%s)((?:\.\w+)+)"%k, lambda m: print(m.groups()) or m.groups()[0]+get_attr_to_item(m.groups()[1][1:]), s)
            
    # @debugger
    def _normalize_column(item):
        
        column = item.column        

        if 'column' in item.source or 'function' in item.source:
            key, sourcefunc = getpropertypair(item.source)
            # if key == 'column': # fix attribute accessors ...
            #     sourcefunc = sourcefunc.split('.')
            #     sourcefunc = sourcefunc[0] + ''.join([ "['%s']"%f for f in sourcefunc[1:]])

            normeddata = executeexpr(sourcefunc, details=testdetails, data=data)
        else:
            raise Exception("Unimplemented normalization source mode: "+str(item.source))
            
        if 'constant' in item.conversion:
            key, constantexpr = getpropertypair(item.conversion)
            constant_factor = executeexpr(constantexpr, details=testdetails)
            normeddata = normeddata * constant_factor             
        elif len(item.conversion) >= 1:
            raise Exception("Unimplemented normalization conversion mode: "+str(item.conversion))
        
        return normeddata
    
    # ====================================================
    # = Process Normalized Columns (one column per item) =
    # ====================================================
    for item in norm_config.columns:
        print(mdHeader(4, "Item: "+item.column.name))
        normedcoldata = _normalize_column(item)
        debug(normedcoldata)
        print("Normed data name:{} shape:{}".format(item.column.label, normedcoldata.shape))
        print()
        
        normcol = DataTree(array=normedcoldata, summary=summaryvalues(normedcoldata, np.s_[0:-1]))
        for slicecol in norm_config.get('_slicecolumns_', []):
            normcol['summaries',slicecol] = columnhandlers.summarize(normedcoldata, slicecol)
        output.append( [ item.column, normcol ] )
    
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
        save_columns(columnmapping=columnmapping, filenames=output.raw.files)
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
        data = DataTree(raw=rawdata['data'])
        columnmapping = normalize_columns(state.details, data, normalized_config, output.norm.files)
        save_columns(columnmapping=columnmapping, filenames=output.norm.files)
    else:
        print("Skipping processing norm stage. File exists: `{}`".format(rawoutfiles.names.matlab))


def process_method(methodname, method, testfolder, projdesc, state):
    
    files = DataTree()
    
    for methoditem in method:
        
        print(mdHeader(3, "Method Item: {} ".format(methoditem.name)))
        # ================================================
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

        process(testfolder=testfolder, data=data, processor=processor, state=state.set(methoditem=methoditem))

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
    
    