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


@debugger
def matchfilename(testfolder, pattern, strictmatch=True):
    files = sorted(testfolder.glob(pattern))
    if strictmatch:
        assert len(files) == 1
    return files[-1]

@debugger
def resolve(url):
    return Path(url).resolve()

def userstrtopath(filepattern, testconfig):    
    return resolve(matchfilename(testconfig.folder.data, filepattern.format(**testconfig.info.name)))
    
    
def load_project_description(testfolder):
    ## temporary, later lookup test config
    project_description = Json.load_json_from(testfolder.projectdescription.resolve())    
    return project_description

def process_metadata(testconfig, projdesc):
    pass



def handle_source_action(name, itemaction, testmethod, env, stage, testconfig):
    action, action_value = getpropertypair(itemaction)
    print(mdBlock("**Action**: {} -> {} ".format(name, action)))

    debug(action_value)
    
    if action == "_csv_":
        filepath = userstrtopath(action_value, testconfig)
        debug(filepath)
    elif action == "_field_":
        print("action -> field")
    elif action == "_lookup_":
        print("action -> lookup")
    
def handle_source(testmethod, methoditems, env, stage, testconfig):
    print(mdHeader(3, "Source: {}.{}".format(stage._name_, testmethod)))

    for itemname, itemaction in methoditems.items():
        handle_source_action(itemname, itemaction, testmethod, env, stage, testconfig)
    
        
    # if isproperty(action, '_csvfile_'):
    #     csvread(Path(item))
    

def process_stage(stage, env, testconfig, projdesc):
    # debug(stage)
    print(mdHeader(2, "Processing Stage: "+stage._name_))

    debug(list(stage.keys()))
    
    # Setup Stage Environment
    var = DataTree()
    env[stage._name_] = var 
    
    sources = { testmethod: handle_source(testmethod, item, var, stage, testconfig) 
                                for testmethod, item in stage._sources_.items() }
    var.update(sources)
    
    
    

def process_project_test(testconfig):
    
    projdesc = load_project_description(testconfig.folder)
    for key in list(flatten(projdesc,sep='.').keys()):
        debug(key)
    print()
    
    env = DataTree()
    metadata = process_metadata(testconfig, projdesc)
    stages = [ process_stage(stage, env, testconfig, projdesc) for stage in projdesc._stages_ ]

    
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
    
    