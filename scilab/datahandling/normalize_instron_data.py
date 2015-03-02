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


def normalize_columns(csvpath, raw_config):
    return 

def process_instron_file(testfolder, csvpath, file_description, version=0, force=DataTree()):
    
    print(mdHeader(3, "File: {} ".format(csvpath.name) ))
    
    header, raw_config, normalized_config = getproperties(file_description)
    
    print(mdHeader(3, "Header"))
    debug(header)
    
    #################################################
    print(mdHeader(3, "Raw Data"))
    rawoutfiles = getfilenames(testfolder, stage="raw", version=version, matlab=True)

    if not 'raw' in force and not rawoutfiles.names.matlab.exists():
        columnmapping = process_raw_columns(csvpath, raw_config, rawoutfiles)
        save_columns(testfolder, stage="raw", columnmapping=columnmapping, filenames=rawoutfiles)
    else:
        print("Skipping processing raw stage. File exists: `{}`".format(rawoutfiles.names.matlab))

    #################################################
    print(mdHeader(3, "Normalize Data"))

    normoutfiles = getfilenames(testfolder, stage="norm", version=version, matlab=True)

    if not 'norm' in force and not rawoutfiles.names.matlab.exists():
        columnmapping = normalize_columns(csvpath, normalized_config, normoutfiles)
        save_columns(testfolder, "normalized", columnmapping=columnmapping, filenames=normoutfiles)
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
    testfolder['datacalc'] = samplefiles / 'data' / 'processed'
    testfolder['raw','csv','instron_test','tracking'] = samplefiles / 'instron-test-file.steps.tracking.csv' 
    testfolder['raw','csv','instron_test','trends'] = samplefiles / 'instron-test-file.steps.trends.csv' 

    process_files(testfolder)
    
if __name__ == '__main__':
    main()
    
    