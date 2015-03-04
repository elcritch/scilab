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

def load_project_description(testfolder):
    ## temporary, later lookup test config
    project_description = Json.load_json_from(testfolder.projectdescription.resolve())    
    return project_description

def process_metadata(testconfig, projdesc):
    pass

    
def handler_file_inputs(action, testconfig):
    if action == "_glob_":
        def _glob_(pattern):
            pattern = pattern.format(**testconfig.info)
            return sorted(testfolder.glob(pattern))[-1]
        return _glob_
    elif action == "_var_":
        def _var_(name):
            return eval(name)


def handler_inputs(name, action, testconfig):
    # "_inputs_": { "csv": { "_csvfile_": "_glob_" },
    if isproperty(action, '_csvfile_'):
        csvread(Path(item))
        
    

def process_stage(stage, testconfig, projdesc):
    # debug(stage)
    print(mdHeader(2, "Processing Stage: "+stage._name_))
    sources = stage._sources_
    computations = stage._computations_

    
    

def process_project_test(testconfig):
    
    projdesc = load_project_description(testconfig.folder)
    for key in list(flatten(projdesc,sep='.').keys()):
        debug(key)
    print()
    
    metadata = process_metadata(testconfig, projdesc)
    stages = [ process_stage(stage, testconfig, projdesc) for stage in projdesc._stages_ ]

    
def main():
    
    samplefiles = Path(__file__).parent.resolve()/'..'/'..'/'test/instron-test-files'
    samplefiles = samplefiles.resolve()
    debug(samplefiles)
    
    ## create fake folder structure 
    testfolder = DataTree()
    testfolder['projectdescription'] = Path(__file__).parent / "project_description.json" 
    testfolder['data'] = samplefiles / 'data' 
    testfolder['details'] = samplefiles / 'data' / 'instron-test.details.json'
    testfolder['datacalc'] = samplefiles / 'data' / 'processed' 
    testfolder['raw','csv','instron_test','tracking'] = samplefiles / 'instron-test-file.steps.tracking.csv' 
    testfolder['raw','csv','instron_test','trends'] = samplefiles / 'instron-test-file.steps.trends.csv' 

    testconfig = DataTree()
    testconfig['info','name'] = "feb07(gf10.4-llm)-wa-tr-l8-x1"
    testconfig['folder'] = testfolder
        
    process_project_test(testconfig)
    
if __name__ == '__main__':
    main()
    
    