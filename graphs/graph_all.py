#!/usr/bin/env python3

import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator

sys.path.insert(0,[ str(p) for p in Path('.').resolve().parents if (p/'scilab').exists() ][0] )

from scilab.tools.project import *
import scilab.tools.scriptrunner as ScriptRunner
from scilab.tools.instroncsv import csvread
import scilab.tools.json as Json
import scilab.tools.project as Project
import scilab.tools.excel as Excel
import scilab.tools.graphing as Graphing
from scilab.tools.graphing import DataMax
import numpy as np

from scilab.graphs.graph_shared import *

def graph(testinfo:TestInfo, testdetails, testdata, testargs):
    
    stepslice = testdata.steps[-1]
    sliced = lambda xs: xs.set(array=xs.array[stepslice])
    debug(stepslice)
    
    # t, y, x = testdata.total_time, testdata.disp, testdata.load
    t, y, x = testdata.total_time, testdata.strain, testdata.stress
    
    ## Setup plot
    fig, axes = plt.subplots(ncols=1, figsize=(14,6))
    ax1 = axes
    ax2 = ax1.twinx()
    
    ## First Plot ##
    ax1_title = "%s vs %s"%(x.label, t.label)
    ax1.plot(t.array, x.array, label=x.label)
    ax1.set_xlabel(t.label)
    ax1.set_ylabel(x.label)
    ax2.set_ylabel(y.label)
    
    ax1.legend(loc=2, fontsize=10)
    ax1.set_title(ax1_title)
    
    ax1_bounds = ax1.get_xbound()
    for step, stepslice in testdata.steps.items():
        ax1.axvline(x=end_y[1], ymin=ax1_bounds, ymax = max(y.array[npslice]), color='purple')
        
    
    ## y2 Plot ##
    ax2.legend(loc=1, fontsize=10)
    ax2.plot(t.array, y.array, color='darkgrey', label=y.label)
    
    # set_secondary_label(ax1, xx=x.strain, xp=data.displacement,
    #             convertfunc=lambda x: x*details.gauge.value)
                
    return fig, axes

def handler(testinfo:TestInfo, testfolder:FileStructure, details:DataTree, testdata:DataTree, args:DataTree):
    
    testname = 'cycles'
    csvdata = testdata.tests[testname].tracking
    
    data = data_configure_load(testinfo=testinfo, data=csvdata, details=details, doLoad=args.doLoad)
    
    data.total_time = csvdata.totalTime
    data.summaries = DataTree()
    
    updated = lambda d1,d2: [ d1.summaries[k].update(v) for k,v in d2.items() ]
    
    data.update( data_normalize(testinfo, data, details) )
    
    ## Save Summaries ##
    testfolder.save_calculated_json(name='summaries', data={'step04_cycles':data.summaries})
    
    ## Figure ##
    fig, ax = graph(testinfo=testinfo, testdata=data, testdetails=details, testargs=args)    
    plt.show(block=True)
    testfolder.save_graph(name='graph_all_'+testname, fig=fig)
    plt.close()
    
    
    return {}

def graphs2_handler(testinfo, testfolder, testdata, args, **kwargs):
    
    return handler(testinfo, testfolder, details=testdata.details, testdata=testdata, args=args, )    

    
if __name__ == '__main__':
    
    import scilab.graphs.graph_runner2
    scilab.graphs.graph_runner2.main()

