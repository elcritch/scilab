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

import numpy as np

def match_data_description(testfolder):
    
    ## temporary, later lookup test config
    project_description_url = Path(__file__).parent / "project_description.json"    
    project_description = Json.load_json_from(project_description_url.resolve())
    
    return project_description


def process_raw_columns(csvpath, raw_config, rawoutfiles):

    rawdata = csvread(csvpath)

    debug(rawdata)
    
    csv_cols_index_full = { v.full: v for v in rawdata.values() if isinstance(v, InstronColumnData) }
    debug(list(csv_cols_index_full.keys()))
    
    output = []
    
    for rawcol in raw_config:
        print(mdBlock("**Raw Column**: {}".format(repr(rawcol))))
        # debug([rawcol])
        
        if rawcol.full not in csv_cols_index_full:
            raise KeyError("Column Missing from Data: column: `{}` data file columns: `{}`".format(repr(rawcol.full), repr(csv_cols_index_full.keys())))
        
        output.append((rawcol, csv_cols_index_full[rawcol.full]))
    
    return output 

# @debugger
def normalize_columns(testdetails, data, config, filenames):
    
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
    
    # @debugger
    def executeexpr(key, expr, **env):
        
        try:
            print("Evaluating key: `{}` with code: `{}`".format(key,expr))
            value = eval(expr, { k: TreeAccessor(v) for k,v in env.items() } )
            print("Evaluated:", value,'\n')
            return value        
        except Exception as err:
            print("executeexpr:env::",env.keys())
            print("executeexpr:env::",env['data'].keys())
            raise err
        
    # @debugger
    def normalize_column(item):
        debug(item)
        
        column = item.column        

        if 'column' in item.source or 'function' in item.source:
            key, sourcefunc = getpropertypair(item.source)
            if key == 'column': # fix attribute accessors ...
                sourcefunc = sourcefunc.split('.')
                sourcefunc = sourcefunc[0] + ''.join([ "['%s']"%f for f in sourcefunc[1:]])

            normeddata = executeexpr(key, sourcefunc, details=testdetails, data=data)
        else:
            raise Exception("Unimplemented normalization source mode: "+str(item.source))
            
        if 'constant' in item.conversion:
            key, constantexpr = getpropertypair(item.conversion)
            constant_factor = executeexpr(key, constantexpr, details=testdetails)
            normeddata = normeddata * constant_factor             
        elif len(item.conversion) >= 1:
            raise Exception("Unimplemented normalization conversion mode: "+str(item.conversion))
        
        return normeddata
        
    for item in config:
        print(mdHeader(4, "Item: "+item.column.name))
        normedcoldata = normalize_column(item)
        debug(normedcoldata)
        print("Normed data name:{} shape:{}".format(item.column.label, normedcoldata.shape))
        print()
        
        output.append( [ item.column, DataTree(array=normedcoldata) ])
    
    
    return output 

def process_instron_file(testfolder, csvpath, file_description, version=0, force=DataTree()):
    
    print(mdHeader(3, "File: {} ".format(csvpath.name) ))
    
    header, raw_config, normalized_config = getproperties(file_description)
    
    print(mdHeader(3, "Header"))
    debug(header)
    
    #################################################
    print(mdHeader(3, "Raw Data"))
    rawoutfiles = getfilenames(testfolder, stage="raw", version=version, matlab=True)

    if not 'raw' in force or not any(k for k,v in rawoutfiles.names.items() if not v.exists()):
        columnmapping = process_raw_columns(csvpath, raw_config, rawoutfiles)
        save_columns(columnmapping=columnmapping, filenames=rawoutfiles)
    else:
        print("Skipping processing raw stage. File exists: `{}`".format(rawoutfiles.names.matlab))

    #################################################
    print(mdHeader(3, "Normalize Data"))

    normoutfiles = getfilenames(testfolder, stage="norm", version=version, matlab=True)

    if not 'norm' in force or not any(k for k,v in normoutfiles.names.items() if not v.exists()):
        testdetails = Json.load_json_from(testfolder.details)
        rawdata = load_columns_matlab(rawoutfiles.names.matlab)
        debug(type(rawdata), rawdata.keys())
        data = {"raw": rawdata['data'] }
        columnmapping = normalize_columns(testdetails, data, normalized_config, normoutfiles)
        save_columns(columnmapping=columnmapping, filenames=normoutfiles)
    else:
        print("Skipping processing norm stage. File exists: `{}`".format(rawoutfiles.names.matlab))


def process_files(testfolder):
    
    
    for key, value in flatten(testfolder.raw,sep='.').items():
        filekind, wavematrix, savemode = key.split('.')[0:]
        csvpath = value
        
        print(mdHeader(2, "Project: {} {} {}".format(filekind, wavematrix, savemode)))
                
        project_description_dict = match_data_description(testfolder)
        
        if filekind == 'csv' and savemode == 'tracking':
            
            file_description = project_description_dict['instron_tracking']
            process_instron_file(testfolder=testfolder, csvpath=csvpath, file_description=file_description)
    
    
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

    process_files(testfolder)
    
if __name__ == '__main__':
    main()
    
    