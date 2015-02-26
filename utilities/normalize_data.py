#!/usr/bin/env python3

import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

sys.path.insert(0,[ str(p) for p in Path('.').resolve().parents if (p/'scilab').exists() ][0] )

from scilab.tools.project import *
from scilab.tools.datatypes import *
import scilab.tools.scriptrunner as ScriptRunner
from scilab.tools.instroncsv import csvread
import scilab.tools.jsonutils as Json
import scilab.tools.project as Project
import scilab.tools.excel as Excel
import scilab.tools.graphing as Graphing
from scilab.tools.graphing import DataMax
import numpy as np

from scilab.graphs.graph_shared import *

@unwrap_array
def getmax(array):
    if not len(array):
        return DataTree(idx=None, value=None)
    idx = np.argmax(array)
    return DataTree(idx=idx, value=array[idx])

@unwrap_array
def getmin(array):
    if not len(array):
        return DataTree(idx=None, value=None)
    idx = np.argmin(array)
    return DataTree(idx=idx, value=array[idx])

@unwrap_array
def summaryvalues(array, sl):
    array = array[]
    return InstronColumnSummary(mean=array[sl].mean(),std=array[sl].std(),mins=get_min(array[sl]),maxs=get_max(array[sl]))

def summarize(colname):
    return DataTree({ key:summaryvalues(data[colname], stepslice).set(slices=sl)
                        for key, stepslice in data.steps.items() })

def dobalances(colname, summary):
    return InstronColumnBalance(step=balancestep, offset=summary[balancestep].mean)
    return balances


@debugger
def data_datasummaries(
        testinfo:TestInfo,
        data:DataTree,
        details:DataTree,
        balancestep=None,
        balances=DataTree(),
        cols=['load', 'disp'],
        ):
    
    datasummaries = DataTree()
    
    # debug('data_datasummaries', cols, balancestep)
    
    # if not balancestep:
        # raise Exception()
    
    assert not (balancestep and balances)
    
        
    for colname in cols:
        summary = summarize(colname)
        
        if colname in balances:
            balance = balances[colname]
        elif balancestep:
            balance = dobalances(colname, summary)
        else:
            balance = InstronColumnBalance(offset=0.0)
        
        datasummaries[colname] = DataTree(balance=balance,summary=summary)

    return datasummaries


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

def normalize_data(testinfo:TestInfo, testdetails, testdata, testargs):
    


def handler(testinfo:TestInfo, testfolder:FileStructure, details:DataTree, testdata:DataTree, args:DataTree):
    
    testname = 'cycles'
    csvdata = testdata.tests[testname].tracking
    
    data = data_configure_load(testinfo=testinfo, data=csvdata, details=details, 
                               balancestep='step_2', data_kind='tracking')
    
    data.total_time = csvdata.totalTime
    # data.summaries = DataTree()
    
    # debug(displayjson(data))
    
    updated = lambda d1,d2: [ d1.summaries[k].update(v) for k,v in d2.items() ]
    
    data.update( data_normalize(testinfo, data, details) )
    
    ## Save Summaries ##
    testfolder.save_calculated_json(name='summaries', data={'step04_cycles':data.summaries})
    
    ## Figure ##
    fig, ax = graph(testinfo=testinfo, testdata=data, testdetails=details, testargs=args)    
    # plt.show(block=True)
    testfolder.save_graph(name='graph_all_'+testname, fig=fig)
    plt.close()
    
    
    return {}

def graphs2_handler(testinfo, testfolder, testdata, args, **kwargs):
    
    return handler(testinfo, testfolder, details=testdata.details, testdata=testdata, args=args, )    

    
if __name__ == '__main__':
    
    import scilab.graphs.graph_runner2
    scilab.graphs.graph_runner2.main()

