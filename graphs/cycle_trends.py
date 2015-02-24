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
    
    stepslice = testdata.steps[5]
    sliced = lambda xs: xs.set(array=xs.array[stepslice])
    debug(stepslice)
    
    t, y, x = sliced(testdata.elapsedCycles), sliced(testdata.disp_max), sliced(testdata.load_max)
    # t, y, x = sliced(testdata.elapsedCycles), sliced(testdata.strain_max), sliced(testdata.stress_max)
    
    ## Setup plot
    fig, axes = plt.subplots(ncols=2, figsize=(14,6))
    (ax1,ax2) = axes
    
    ## First Plot ##
    ax1_title = "%s vs %s"%(x.label, t.label)
    ax1.plot(t.array, x.array)
    ax1.set_xlabel(t.label)
    ax1.set_ylabel(x.label)
    
    # stress_max = .stress_max.mean
    # ax1.hlines(stress_max, x.array[0],x.array[-1], linestyles='dashed')
    
    # label_stress_max = "Stress Peak Avg: {:.2f} [{}]".format(x.array[y.summary.maxs.idx], x.units, )
    # debug(label_stress_max)    
    # graph_annotation_data(ax1, label_stress_max, xy=uts_peak,)
    
    # ax1.set(xlim=limiter(t.array, 0.08), ylim=limiter(x.array, 0.8))
    ax1.legend(loc=0, fontsize=10)
    ax1.set_title(ax1_title)
    
    ## Second Plot ##
    ax2_title = "%s vs %s"%(y.label, t.label, )
    
    ax2.plot(t.array, y.array)
    ax2.set_xlabel(t.label)
    ax2.set_ylabel(y.label)
    
    # ax2.set(xlim=limiter(t.array, 0.08), ylim=limiter(y.array, 0.08))
    ax2.legend(loc=0, fontsize=10)
    ax2.set_title(ax2_title)

    fig.subplots_adjust(hspace=1.4, )
    
    # Make some room at the bottom 
    fig.subplots_adjust(bottom=0.20, left=0.20, right=0.80, top=0.90)
    
    # set_secondary_label(ax1, xx=data.strain, xp=data.displacement,
    #             convertfunc=lambda x: x*details.gauge.value)
    #
    # set_secondary_label(ax1, xx=data.stress, xp=data.load, ax_dir='y', side='right',
    #             convertfunc=lambda x: x*details.measurements.area.value, position=('outward',0))
        
    return fig, axes

def handler(testinfo:TestInfo, testfolder:FileStructure, details:DataTree, testdata:DataTree, args:DataTree):
    
    cyclesdata = testdata.tests.cycles.trends
    
    data = data_configure_load(testinfo=testinfo, data=cyclesdata, details=details, trends=True)
    
    data.elapsedCycles = cyclesdata.elapsedCycles
    data.summaries = DataTree()
    
    updated = lambda d1,d2: [ d1.summaries[k].update(v) for k,v in d2.items() ]
    
    data.update( data_normalize(testinfo, data, details, suffix='max') )
    data.update( data_normalize(testinfo, data, details, suffix='min') )
    
    debug(data.summaries.keys())
    
    fig, ax = graph(testinfo=testinfo, testdata=data, testdetails=details, testargs=args)
    imgname = 'fatigue graphs | name=cycle trends | test=%s | v5 |.png'%str(testinfo)
    
    imgpath = testfolder.graphs.resolve() / imgname 
    debug(imgpath)    

    plt.show(block=True)
    
    fig.savefig(str(imgpath), bbox_inches='tight',)    
    plt.close()
    
    return {}

def graphs2_handler(testinfo, testfolder, testdata, args, **kwargs):
    
    return handler(testinfo, testfolder, details=testdata.details, testdata=testdata, args=args, )    

    
if __name__ == '__main__':
    
    import scilab.graphs.graph_runner2
    scilab.graphs.graph_runner2.main()

