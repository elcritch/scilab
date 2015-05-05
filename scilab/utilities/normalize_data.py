#!/usr/bin/env python3

import os, sys, pathlib
# sys.path.insert(0,[ str(p) for p in pathlib.Path('.').resolve().parents if (p/'scilab').exists() ][0] )


from scilab.tools.project import *
from scilab.expers.configuration import *

import numpy as np

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
    array = array[sl]
    return InstronColumnSummary(mean=array[sl].mean(),std=array[sl].std(),mins=getmin(array[sl]),maxs=getmax(array[sl]))

def summarize(testdata, colname):
    return DataTree({ key:summaryvalues(testdata[colname], stepslice).set(slices=stepslice)
                        for key, stepslice in testdata.steps.items() })

def dobalances(colname, summary):
    return InstronColumnBalance(step=balancestep, offset=summary[balancestep].mean)


@debugger
def data_datasummaries(
        testinfo:BasicTestInfo,
        data:DataTree,
        details:DataTree,
        balancestep=None,
        balances=DataTree(),
        cols=['load', 'disp'],
        ):
    
    datasummaries = DataTree()
            
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


def data_normalize_col(testinfo:BasicTestInfo, data:DataTree, details:DataTree, 
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

def normalize_data(testinfo:BasicTestInfo, testdetails, testdata, testargs):
    pass


def handler(testinfo:BasicTestInfo, testfolder:FileStructure, details:DataTree, testdata:DataTree, args:DataTree):
    
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

    
if __name__ == '__main__':
    
    with Tests(quiet=False, ) as tests:
    
        foobar = []
    
        @test_in(tests)
        def test_debug():
            pass
        
