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


def executeexpr(key, expr, env):
    
    try:
        # change 'data.a.b.c' accesses into getitem style data['a']['b']...
        # expr = re_attribs('data',expr) 
        print("Evaluating key: `{}` with code: `{}`".format(key,expr))
        
        value = eval(expr, env)
        print("Evaluated:", value,'\n')
        return value        
    except Exception as err:
        print("executeexpr:env::",env.keys())
        # print("executeexpr:env::",env['data'].keys())
        raise err

def process_metadata(testconfig, projdesc):
    pass

# @debugger
def action_lookup(value:dict, action, state, testconfig):
    lookupexpr, lookupoptions = getpropertypair(value)
    
    lookupvalue = executeexpr(action, lookupexpr, state.env)
    debug(lookupvalue)
    lookupname = lookupoptions.get(lookupvalue, None)
    if lookupvalue in lookupoptions.keys():
        return action_field(lookupname, action, state, testconfig)
    elif "_default_" in options:
        print(mdBlock("Warning: Could not find: `{}`, choosing default. ", lookupvalue))
        return action_field("_default_", action, state, testconfig)
    else:
        debug(lookupexpr, lookupoptions)
        debug({ k:'' for k in flatten(state.env, sep=".").keys() })
        msg = mdBlock("Error: Could not find: `{}`", lookupvalue)
        raise ProcessorException(msg.strip())

# @debugger
def action_field(value:str, action, state, testconfig):
    
    result = executeexpr(action, value, state.env)
    return result

# @debugger
def action_csv(value, action, state, testconfig):
    filepath = userstrtopath(value, testconfig)
    debug(filepath)
    data = csvread(filepath)
    return data

def handle_source_action(name, itemaction, testmethod, state, testconfig):
    action, action_value = getpropertypair(itemaction)
    print(mdBlock("**Action**: {} -> {} -> {}".format(name, action, action_value)))

    # debug(action_value)
    
    try:
        action_handler = {
            "_csv_":    action_csv,
            "_field_":  action_field,
            "_lookup_": action_lookup,
        }[action]
        action_handler.__name__ = action
        sourceret = action_handler(action_value, action, state, testconfig)
        debug(action_handler)
        debug(sourceret)
        
        return sourceret
    except ProcessorException as err:
        msg = "__Problem executing source action__: {} -> {} :: {}".format(name, action, err)
        print(mdBlock(msg))
        raise ProcessorException(msg)

def handle_computation_columns(columninfo, columndata, state, testconfig):
    
    # data = DataTree(data)
    # shortdetails = DataTree(testdetails)
    # testdetails.__dict__['_ignore'] = ['summaries']
    # debug(type(data))
    # debug(data.keys())
    # print('\n')
    
    output = []
    
    # @debugger
    def normalize_column(item, source):
        debug(item)
        
        column = item.column
        
        key, sourcefunc = getpropertypair(source)
        
        if key == '_stage_':
            field = getpropertypair(source)[1] 
            # key, sourcefunc = '_field_',
            # debug(key, sourcefunc, columndata)
            normeddata = columndata[item.column.name]
            # normeddata = action_lookup(source, key, state, testconfig)
            # normeddata = executeexpr(key, sourcefunc, state.env.set(data=columndata))
        elif key == '_lookup_':
            key, sourcefunc = getpropertypair(source)
            normeddata = action_field(source, key, state, testconfig)
        elif key == '_field_':
            key, sourcefunc = getpropertypair(source)
            debug(key, sourcefunc)
            normeddata = executeexpr(key, sourcefunc, state.env)
            # raise Exception(normeddata)
            
        else:
            raise Exception("Unimplemented normalization source mode: "+str(source))
            
        if '_constant_' in item.get('conversion',{}):
            key, constantexpr = getpropertypair(item.conversion)
            constant_factor = executeexpr(key, constantexpr, details=testdetails)
            normeddata = normeddata * constant_factor             
        elif len(item.get('conversion',{})) >= 1:
            raise Exception("Unimplemented normalization conversion mode: "+str(item.conversion))
        
        return normeddata
        
    debug(columninfo, state.sourceitemname)
    cols = tuple(columninfo.split('.'))
    debug(cols)
    colconfs = state.env['_shared_'][cols]
    debug(colconfs)
    columnconfigs = colconfs[state.sourceitemname]
    stagesource = colconfs.get('_source_',DataTree())
    debug(columnconfigs)
    
    for item in columnconfigs:
        source = item.get('_source_',stagesource)
                    
        print(mdHeader(4, "Column name: `{}` from source: `{}`",item.column.name, source))
        normedcoldata = normalize_column(item, source)
        debug(normedcoldata)
        print("Normed data name:{} shape:{}".format(item.column.label, normedcoldata.shape))
        print()
        
        output.append( [ item, DataTree(array=normedcoldata) ])
    
    debug(output)
    return DataTree(output) 


def handle_computations(source_data, computations, itemname, state, testconfig):
    
    debug(list(source_data.keys()))
    
    data = source_data
    
    for compname, compvalue in computations.items():
        print(mdHeader(4, "Computation: {}", compname))
        
        compfunc = {
            '_columns_': handle_computation_columns,
        }[compname]
        
        data = compfunc(compvalue, data, state.set(computations=computations, sourceitemname=itemname), testconfig)
        debug(data)
        
    # raise Exception(data)
    return data
    
    
def handle_source(testmethod, methoditems, state, testconfig):
    print(mdHeader(3, "Source: {}.{}".format(state.stage._name_, testmethod)))

    stage_inputs = [ k for k,v in state.stage._inputs_.items() if v == "_stage_" ]
    debug(stage_inputs)
    
    if not all([ si in state.env.keys() for si in stage_inputs ]):
        print(mdBlock("Required input stages not loaded into the environment: env: {} input stages: {}", env.keys(), stage_inputs))
        return DataTree()

    source_inputs = DataTree()    
    for itemname, itemaction in methoditems.items():
        try:
            itemstate = state.set(testmethod=testmethod, methoditem=itemname)
            ret = handle_source_action(itemname, itemaction, testmethod, itemstate, testconfig)
            debug(ret.keys())
            source_inputs[itemname] = ret
            
        except ProcessorException as err:
            print(mdBlock("Problem processing source: {}, for stage: {}, err: {}".format(testmethod, state.stage._name_, err)))
            raise err
    
    debug(source_inputs)
    
    source_outputs = DataTree()    
    for itemname, itemaction in methoditems.items():
        try:
            computations = DataTree()
            computations.update(state.stage.get("_computations_", {}))
            computations.update(itemaction.get("_computations_", {}))
            
            source_input = source_inputs.get(itemname, DataTree())
            ret = handle_computations(source_input, computations, itemname, itemstate, testconfig)
            
            source_outputs[itemname] = ret
            
        except ProcessorException as err:
            print(mdBlock("Problem processing source: {}, for stage: {}, err: {}".format(testmethod, state.stage._name_, err)))
            raise err
    
    debug(source_outputs)
    
    return source_outputs

def load_testdetails(env, testconfig):
    # update and merge json file
    # <TODO>
    
    # read json file
    testconfig.details = Json.load_json_from(testconfig.folder.details)
    env.details = testconfig.details
    

def process_stage(stage, env, testconfig, projdesc):
    # debug(stage)
    
    print(mdHeader(2, "Processing Stage: "+stage._name_))
    load_testdetails(env, testconfig)
    
    # Setup Stage Environment
    
    try:
        state = DataTree()
        state.stage = stage
        state.env = env
        
        sources = { testmethod: handle_source(testmethod, item, state, testconfig) 
                                    for testmethod, item in stage._sources_.items() }
        
        env[stage._name_] = DataTree(sources)
                                    
        if stage._name_ == 'pre':
            raise Exception("done")
        
    except Exception as err:
        print(mdHeader(3, "Error Processing Stage: {}", stage._name_))
        debug(stage)
        print()
        kenv = sorted((k,str(type(v)).replace('<','')) for k,v in flatten(env,sep='.',ignore=['__builtins__', 'summaries']).items() if not 'summaries' in k)
        debug(OrderedDict(kenv))
        
        raise err
                            
    print(mdHeader(3, "Finished processing Stage: {}", stage._name_))
    # debug(sources)
    
    

def process_project_test(testconfig):
    
    projdesc = load_project_description(testconfig.folder)
    for key in list(flatten(projdesc,sep='.').keys()):
        debug(key)
    print()
    
    env = DataTree()
    metadata = process_metadata(testconfig, projdesc)
    
    env['_metadata_'] = metadata
    # env['_projdesc_'] = projdesc
    env['_shared_'] = projdesc.get('_shared_', DataTree())
    
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
    
    