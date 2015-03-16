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
import scilab.tools.jsonutils as Json
import scilab.tools.project as Project
import scilab.tools.excel as Excel
import scilab.tools.graphing as Graphing
from scilab.tools.graphing import DataMax
import numpy as np

from scilab.graphs.graph_shared import *

def graph(test, matdata, args, zconfig=DataTree()):
    
    step_idx = args.get('step_idx', 'idx_neg1')
    
    data, info, indexes = matdata.data, matdata.columninfo, matdata.indexes
    stepslice = getattr(indexes.step,step_idx)
    sliced = lambda xs: xs.set(array=data.xs[stepslice])
    
    if zconfig['stage'] == "norm":
        t, x, y = data.totalTime, data.stress, data.strain
        info_t, info_x, info_y = info.totalTime, info.stress, info.strain
    else:
        t, x, y = data.totalTime, data.disp, data.load
        info_t, info_x, info_y = info.totalTime, info.disp, info.load
    
    ## Setup plot
    fig, axes = plt.subplots(ncols=1, figsize=(14,6))
    ax1 = axes
    ax2 = ax1.twinx()
    
    ## First Plot ##
    ax1_title = "Graph All: {} ({})".format(test.info.short, repr(zconfig))
    ax1.plot(t, x, label=info_x.label)
    ax1.set_xlabel(info_t.label)
    ax1.set_ylabel(info_x.label)
    ax2.set_ylabel(info_y.label)
    
    ax1.legend(loc=2, fontsize=10)
    ax1.set_title(ax1_title)
    
    for idx in indexes.step._fieldnames:
        sl = getattr(indexes.step, idx)
        # debug(idx, sl)
        ax1.axvline(t[stepslice[0]], *ax1.get_ybound(), color='purple')
        
    
    ## y2 Plot ##
    ax2.plot(t, y, color='darkgrey', label=info_y.label)
    ax2.legend(loc=1, fontsize=10)
    
    # set_secondary_label(ax1, xx=stress.strain, xp=data.displacement,
    #             convertfunc=lambda stress: x*details.gauge.value)
                
    return fig, axes

def handler(testinfo:TestInfo, testfolder:FileStructure, details:DataTree, testdata:DataTree, args:DataTree):
    
    testname = 'cycles'
    csvdata = testdata.tests[testname].tracking
    
    data = data_configure_load(testinfo=testinfo, data=csvdata, details=details, 
                               balancestep='step_2', data_kind='tracking')
    
    data.total_time = csvt
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

