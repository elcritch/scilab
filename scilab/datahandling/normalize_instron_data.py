#!/usr/bin/env python3

import os, sys, pathlib


# sys.path.insert(0,[ str(p) for p in pathlib.Path('.').resolve().parents if (p/'scilab').exists() ][0] )


from scilab.tools.project import *
from scilab.expers.configuration import *
from scilab.tools.instroncsv import *
import scilab.tools.jsonutils as Json

import numpy as np


def data_normalize_col(testinfo:TestInfo, data:DataTree, details:DataTree, 
                    normfactor, xname, yname, yunits, balance, 
                    ):

    normalized = DataTree(steps=data.steps)
    if xname in data.summaries:
        normalized.summaries
    normalized.summaries.update(data_datasummaries(testinfo, data=data, details=details, cols=[xname]))
    
    # offset_load = data[loadname].array - data.summaries[xname].balance
    # normalized[loadname] = data[loadname].set(array=offset_load)
    
    ydata = data[dispname].array / normfactor
    normalized[stressname] = DataTree(array=stress, label=stressname.capitalize(), units=stressunits)

    normalized.summaries.update(data_datasummaries(testinfo, normalized, details, cols=[strainname, stressname]))

    normalized.summaries[strainname].balance = normalized.summaries[dispname].balance / details.gauge.value
    normalized.summaries[stressname].balance = normalized.summaries[loadname].balance / details.measurements.area.value
    
    return normalized


def process_columns(columns):
    
    pass
    
    
def process_csv_file(rawdata, dataconfig):
    
    rawdata = csvread(csvpath)

    debug(rawdata.keys())
    
    # ColumnInfo('name label details units full idx')

def match_data_description(testfolder):
    project_description_url = Path(__file__).parent / "project_description.json"
    debug(project_description_url)
    project_description_url = project_description_url.resolve()
    
    project_description = Json.load_json_from(project_description_url)
    
    return project_description

def process_instron_file(testfolder, csvpath,savemode,filekind):
    
    print(mdHeader(3, "File: {} ".format(csvpath.name) ))
    
    debug(locals())
    
    project_description = match_data_description(testfolder)
    debug(project_description)
    
    

    
def process_files(testfolder):
    
    for key, value in flatten(testfolder,sep='.').items():
        filekind, wavematrix, savemode = key.split('.')[1:]
        csvpath = value
        process_instron_file(testfolder=testfolder, csvpath=csvpath, savemode=savemode, filekind=filekind)
    
    
def main():
    
    samplefiles = Path(__file__).parent.resolve()/'..'/'..'/'test/instron-test-files'
    samplefiles = samplefiles.resolve()
    debug(samplefiles)
    
    ## create fake folder structure 
    testfolder = DataTree()
    testfolder['raw','csv','instron_test','tracking'] = samplefiles / 'instron-test-file.steps.tracking.csv' 
    testfolder['raw','csv','instron_test','trends'] = samplefiles / 'instron-test-file.steps.trends.csv' 

    process_files(testfolder)
    
if __name__ == '__main__':
    main()
    
    