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

def process_metadata(testconfig, projdesc):
    pass

# @debugger
def action_lookup(value:dict, action, env, stage, testconfig):
    lookupexpr, lookupoptions = getpropertypair(value)
    
    lookupvalue = eval(lookupexpr, env)
    debug(lookupvalue)
    lookupname = lookupoptions.get(lookupvalue, None)
    if lookupvalue in lookupoptions.keys():
        return action_field(lookupname, action, env, stage, testconfig)
    elif "_default_" in options:
        print(mdBlock("Warning: Could not find: `{}`, choosing default. ", lookupvalue))
        return action_field("_default_", action, env, stage, testconfig)
    else:
        debug(lookupexpr, lookupoptions)
        debug({ k:'' for k in flatten(env, sep=".").keys() })
        msg = mdBlock("Error: Could not find: `{}`", lookupvalue)
        raise ProcessorException(msg.strip())

# @debugger
def action_field(value:str, action, env, stage, testconfig):
    result = eval(value, env)
    return result

# @debugger
def action_csv(value, action, env, stage, testconfig):
    filepath = userstrtopath(value, testconfig)
    debug(filepath)
    data = csvread(filepath)
    return data

def handle_source_action(name, itemaction, testmethod, env, stage, testconfig):
    action, action_value = getpropertypair(itemaction)
    print(mdBlock("**Action**: {} -> {} -> {}".format(name, action, action_value)))

    # debug(action_value)
    
    try:
        action_handler = {
            "_csv_":    action_csv,
            "_field_":  action_field,
            "_lookup_": action_lookup,
        }[action]
        
        return action_handler(action_value, action, env, stage, testconfig)
    except ProcessorException as err:
        msg = "__Problem executing source action__: {} -> {} :: {}".format(name, action, err)
        print(mdBlock(msg))
        raise ProcessorException(msg)

def handle_source(testmethod, methoditems, env, stage, testconfig):
    print(mdHeader(3, "Source: {}.{}".format(stage._name_, testmethod)))

    output = DataTree()
    stage_inputs = [ k for k,v in stage._inputs_.items() if v == "_stage_" ]
    debug(stage_inputs)
    
    if not all([ si in env.keys() for si in stage_inputs ]):
        print(mdBlock("Required input stages not loaded into the environment: env: {} input stages: {}", env.keys(), stage_inputs))
        return output
    
    for itemname, itemaction in methoditems.items():
        try:
            ret = handle_source_action(itemname, itemaction, testmethod, env, stage, testconfig)
            # debug(ret, itemname)
            output[itemname] = ret
        except ProcessorException as err:
            print(mdBlock("Problem processing source: {}, for stage: {}, err: {}".format(testmethod, stage._name_, err)))
            raise err
    
    debug(output.keys())
    
    return output

def load_testdetails(env, testconfig):
    # update and merge json file
    # <TODO>
    
    # read json file
    env.details = Json.load_json_from(testconfig.folder.details)
    

def process_stage(stage, env, testconfig, projdesc):
    # debug(stage)
    
    print(mdHeader(2, "Processing Stage: "+stage._name_))
    load_testdetails(env, testconfig)
    
    # Setup Stage Environment
    env[stage._name_] = DataTree(_stage_=stage._name_)
    
    try:
        sources = { testmethod: handle_source(testmethod, item, env, stage, testconfig) 
                                    for testmethod, item in stage._sources_.items() }
    except Exception as err:
        print(mdHeader(3, "Error Processing Stage: {}", stage._name_))
        debug(stage)
        debug(flatten(env,sep='.').keys())
        
        raise err
                            
    print(mdHeader(3, "Finished processing Stage: {}", stage._name_))
    # debug(sources)
    
    env[stage._name_].update(**sources)
    

def process_project_test(testconfig):
    
    projdesc = load_project_description(testconfig.folder)
    for key in list(flatten(projdesc,sep='.').keys()):
        debug(key)
    print()
    
    env = DataTree()
    metadata = process_metadata(testconfig, projdesc)
    
    env['_metadata_'] = metadata
    
    stages = [ (stage._name_, process_stage(stage, env, testconfig, projdesc)) 
                for stage in projdesc._stages_ ]

    # debug(stages)

    
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
    
    