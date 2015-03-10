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

# import pdb

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

def handle_source_action(name, methoditem_action, testmethod, state, testconfig):
    action, action_value = getpropertypair(methoditem_action)
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
        # debug(sourceret)
        
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
        
        key, sourceval = getpropertypair(source)
        
        if key == '_stage_':
            # key, sourceval = '_field_',
            debug(key, sourceval, columndata)
            colstr = sourceval.format(**flatten(item,sep='_'))
            normeddata = columndata[colstr]
            
            raise Exception(key, sourceval, columndata)
            
            # normeddata = action_fieldon_lookup(source, key, state, testconfig)
            # normeddata = executeexpr(key, sourceval, state.env.set(data=columndata))
        elif key == '_lookup_':
            key, sourceval = getpropertypair(source)
            normeddata = action_field(source, key, state, testconfig)
            
        elif key == '_field_':
            key, sourceval = getpropertypair(source)
            debug(key, sourceval)
            normeddata = executeexpr(key, sourceval, state.env)
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
        
    # debug(columninfo, state.testsourcemethoditem)
    cols = tuple(columninfo.split('.'))
    # debug(cols)
    colconfs = state.env['_shared_'][cols]
    # debug(colconfs)
    columnconfigs = colconfs[state.testsourcemethoditem]
    stagesource = colconfs.get('_source_',DataTree())
    # debug(columnconfigs)
    
    for item in columnconfigs:
        source = item.get('_source_',stagesource)
                    
        print(mdHeader(4, "Column name: `{}` from source: `{}`",item.column.name, source))
        normedcoldata = normalize_column(item, source)
        # debug(normedcoldata)
        print("Normed data name:{} shape:{}".format(item.column.label, normedcoldata.shape))
        print()
        
        output.append( [ item, DataTree(array=normedcoldata) ])
    
    # debug(output)
    return DataTree(output) 


def handle_method_computations(source_data, computations, methoditem_val, state, testconfig):
    
    # debug(list(source_data.keys()))
    
    data = source_data
    
    for compname, compvalue in computations.items():
        print(mdHeader(4, "Computation: {}", compname))
        
        compfunc = {
            '_columns_': handle_computation_columns,
        }[compname]
        
        data = compfunc(compvalue, data, state.set(computations=computations, testsourcemethoditem=methoditem_val), testconfig)
        # debug(data)
        
    # raise Exception(data)
    return data
    
    
def handle_inputs(testmethod, methoditems, state, testconfig):
    print(mdHeader(3, "Source: {}.{}".format(state.stage._name_, testmethod)))

    ## Check for previous stages (?)
    stage_inputs = [ k for k,v in state.stage._inputs_.items() if v == "_stage_" ]
    debug(stage_inputs)
    
    if not all([ si in state.env.keys() for si in stage_inputs ]):
        print(mdBlock("Required input stages not loaded into the environment: env: {} input stages: {}", env.keys(), stage_inputs))
        return DataTree()
    
    ## Configure inputs
    source_inputs = DataTree()    
    for methoditem_val, methoditem_action in sorted(methoditems.items()):
        try:
            itemstate = state.set(testmethod=testmethod, methoditem=methoditem_val)
            ret = handle_source_action(methoditem_val, methoditem_action, testmethod, itemstate, testconfig)
            debug(methoditem_val)
            source_inputs[methoditem_val] = ret
            
        except ProcessorException as err:
            print(mdBlock("Problem processing source: {}, for stage: {}, err: {}".format(testmethod, state.stage._name_, err)))
            raise err
    
    # debug(source_inputs)
    
    return source_inputs
    

def handle_sources(testmethod, methoditems, state, testconfig):

    ## Configure sources
    source_outputs = DataTree()    
    for methoditem_val, methoditem_action in sorted(methoditems.items()):
        try:
            itemstate = state.set(testmethod=testmethod, methoditem=methoditem_val)
            ret = handle_source_action(methoditem_val, methoditem_action, testmethod, itemstate, testconfig)
            debug(list(ret.keys()))
            source_outputs[methoditem_val] = ret
            
        except ProcessorException as err:
            print(mdBlock("Problem processing source: {}, for stage: {}, err: {}".format(testmethod, state.stage._name_, err)))
            raise err
    
    # debug(source_inputs)
    
    return source_outputs
    
def handle_computations(testmethod, methoditems, state, testconfig):
    
    ## Handle Computations
    computation_outputs = DataTree()    
    for methoditem_val, methoditem_action in sorted(methoditems.items()):
        try:
            debug(computation_outputs, methoditem_val, methoditem_action)
            computations = DataTree()
            computations.update(state.stage.get("_computations_", {}))
            computations.update(methoditem_action.get("_computations_", {}))
            
            debug(flatten_type(state))
            
            source_input = state[state.stage._name_, 'sources', testmethod, methoditem_val]
            itemstate = state.set(testmethod=testmethod, methoditem=methoditem_val)
            ret = handle_method_computations(source_input, computations, methoditem_val, itemstate, testconfig)
            
            source_outputs[methoditem_val] = ret
            
        except ProcessorException as err:
            print(mdBlock("Problem processing source: {}, for stage: {}, err: {}".format(testmethod, state.stage._name_, err)))
            raise err
    
    # debug(computation_outputs)
    
    return computation_outputs
    

def load_testdetails(env, testconfig):
    # update and merge json file
    # <TODO>
    
    # read json file
    testconfig.details = Json.load_json_from(testconfig.folder.details)
    env.details = testconfig.details
    

def flatten_type(d, ignore=['__builtins__', 'summaries']):
    kenv = sorted((k,str(type(v)).replace('<','')) for k,v in flatten(d,sep='.',ignore=ignore).items() if not 'summaries' in k)
    return OrderedDict(kenv)

def process_stage(stage, env, testconfig, projdesc):
    # debug(stage)
    
    print(mdHeader(2, "Processing Stage: "+stage._name_))
    load_testdetails(env, testconfig)
    
    # Setup Stage Environment
    
    try:
        state = DataTree()
        state.stage = stage
        state.env = env

        ## process inputs
        inputs = { testmethod: handle_inputs(testmethod, item, state, testconfig) 
                                    for testmethod, item in stage._inputs_.items() }
        
        env[stage._name_, 'inputs'] = DataTree(inputs)
        
        ## process sources
        sources = { testmethod: handle_sources(testmethod, item, state, testconfig) 
                                    for testmethod, item in stage._sources_.items() }
        state.sources = sources
        
        debug(sources.keys())
        env[stage._name_, 'sources'] = DataTree(sources)
        
        ## process computations
        outputs = { testmethod: handle_computations(testmethod, item, state, testconfig) 
                                    for testmethod, item in stage._sources_.items() }
        
        state.outputs = outputs
        env[stage._name_, 'outputs'] = DataTree(outputs)
                                    
        if stage._name_ == 'pre':
            raise Exception("done")
        
    except Exception as err:
        print(mdHeader(3, "Error Processing Stage: {}", stage._name_))
        debug(stage)
        print()
        # kenv = sorted((k,str(type(v)).replace('<','')) for k,v in flatten(env,sep='.',ignore=['__builtins__', 'summaries']).items() if not 'summaries' in k)
        debug(flatten_type(env))
        
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
    
    