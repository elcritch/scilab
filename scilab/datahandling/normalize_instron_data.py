#!/usr/bin/env python3

import os, sys, pathlib, re
import pandas as pd
import numpy as np
import scipy.io as sio
from pandas import ExcelWriter

# sys.path.insert(0,[ str(p) for p in pathlib.Path('.').resolve().parents if (p/'scilab').exists() ][0] )


from scilab.tools.project import *
from scilab.expers.configuration import *
from scilab.tools.instroncsv import *
import scilab.tools.jsonutils as Json

import numpy as np

def getproperty(json_object):
    return next(json_object.values().__iter__())

def getproperties(json_array):
    return [ getproperty(item) for item in json_array ]


def match_data_description(testfolder):
    
    ## temporary, later lookup test config
    project_description_url = Path(__file__).parent / "project_description.json"    
    project_description = Json.load_json_from(project_description_url.resolve())
    
    return project_description

def clean(s):
    return s.replace("·",".")

def process_raw_columns(csvpath, raw_config):

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

def save_columns(testfolder, name, columnmapping, version=0):
    
    filename = testfolder.datacalc / '{name} | v{ver}.txt'.format(name=name, ver=version)
    orderedmapping = OrderedDict( (k.name, v.array) for k,v in columnmapping ) 
    
    with ExcelWriter(str(filename.with_suffix('.xlsx'))) as writer:
        # [ENH: Better handling of MultiIndex with Excel](https://github.com/pydata/pandas/issues/5254)
        # [Support for Reading Excel Files with Hierarchical Columns Names](https://github.com/pydata/pandas/issues/4468)
        print("Creating excel file...")
        df1 = pd.DataFrame( orderedmapping )
        df2 = pd.DataFrame( [ k[0] for k in columnmapping ] )
        df1.to_excel(writer,'Data')
        df2.to_excel(writer,'ColumnInfo')
        print("Writing excel file...")
        writer.save()
    
    with open(str(filename.with_suffix('.mat')),'wb') as outfile:
        print("Writing matlab file...")
        sio.savemat(outfile, {"data":orderedmapping, "columns": [k[0] for k in columnmapping ] } , 
                    appendmat=False, 
                    format='5',
                    long_field_names=False, 
                    do_compression=True,
                    )
        

def process_instron_file(testfolder, csvpath, file_description):
    
    print(mdHeader(3, "File: {} ".format(csvpath.name) ))
    
    header, raw_config, normalized_config = getproperties(file_description)
    
    print(mdHeader(3, "Header"))
    debug(header)
    
    print(mdHeader(3, "Raw Data"))
    save_columns(testfolder, "raw", process_raw_columns(csvpath, raw_config))

    print(mdHeader(3, "Normalize Data"))
    

    
def process_files(testfolder):
    
    for key, value in flatten(testfolder.raw,sep='.').items():
        filekind, wavematrix, savemode = key.split('.')[0:]
        csvpath = value
        
        debug(filekind, wavematrix, savemode, csvpath.name)
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
    
    