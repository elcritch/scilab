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

namedtuple("Test", "info, folder, details, data, headers")

def graph(info, folder, details, data, headers, args):
    
    stepslice = testdata.steps['step_5']
    sliced = lambda xs: xs.set(array=xs[stepslice])
    # debug(stepslice)
    # debug(list(testdata))
    other = testdetails.other
    xname, yname = 'stress_max', 'strain_max'
    t, y, x = sliced(testdata.elapsedCycles), sliced(testdata.strain_max), sliced(testdata.stress_max)
    
    calc = DataTree()
    calc[xname] = DataTree()
    calc[xname].target = other.test_max_force / testdetails.measurements.area.value
    calc[xname].stress_level = int(100*other.stress_level)
    calc[xname].pred_max = other.uts_stress # *testdetails.measurements.area.value
    calc[xname].actual = x.mean() 
    calc[xname].actual_perc = calc[xname].actual/(calc[xname].pred_max) * 100.0
    
    # debug(calc)
    
    ## Setup plot
    fig, axes = plt.subplots(ncols=2, figsize=(14,6))
    (ax1,ax2) = axes
    
    ## First Plot ##
    ax1_title = "%s vs %s"%(datainfo.x.label, datainfo.t.label)
    ax1.plot(t, x)
    ax2.set_xlabel(labeler(t))
    ax2.set_ylabel(labeler(x))
    
    # stress_max = .stress_max.mean
    ax1.hlines(-testdata.summaries[xname].balance.offset, *ax1.get_xbound(), linestyles='dashed', label='Offset', color='lightgrey')
    
    avg_label='Avg. {:3.1f} ({:.0f}%)'.format(calc[xname].actual, calc[xname].actual_perc)    
    tgt_label='Tgt. {:3.1f} (SL{})'.format(calc[xname].target, calc[xname].stress_level)
    pred_label='PredMax. {:3.1f} (SL{})'.format(calc[xname].pred_max, calc[xname].stress_level)
    
    ax1.hlines(calc[xname].actual, *ax1.get_xbound(), linestyles='dashed', label=avg_label, color='black')
    ax1.hlines(calc[xname].target, *ax1.get_xbound(), linestyles='dashed', label=tgt_label, color='orange')
    ax1.hlines(calc[xname].pred_max, *ax1.get_xbound(), linestyles='dashed', label=pred_label, color='red')
    
    # label_stress_max = "Stress Peak Avg: {:.2f} [{}]".format(x[y.summary.maxs.idx], x.units, )
    # debug(label_stress_max)
    # graph_annotation_data(ax1, label_stress_max, xy=uts_peak,)
    
    # ax1.set(xlim=limiter(t, 0.08), ylim=limiter(x, 0.8))
    ax1.legend(loc=3, fancybox=True, framealpha=0.0, )
    ax1.set_title(ax1_title)
    
    ## Second Plot ##
    
    y_target = other.precond_disp    
    
    ax2_title = "%s vs %s"%(dh.y.label, dh.t.label, )
    
    ax2.plot(t, y)
    ax2.set_xlabel(labeler(t))
    ax2.set_ylabel(labeler(y))
    
    ax2.hlines(y_target, *ax2.get_xbound(), linestyles='dashed', label='Targ. '+dh.y.label)
    
    # ax2.set(xlim=limiter(t, 0.08), ylim=limiter(y, 0.08))
    ax2.legend(loc='best', fontsize=10,fancybox=True, framealpha=0.5)
    ax2.set_title(ax2_title)

    fig.subplots_adjust(hspace=1.4, )
    
    # Make some room at the bottom 
    fig.subplots_adjust(bottom=0.20, left=0.20, right=0.80, top=0.90)
    
    # set_secondary_label(ax1, xx=data.strain, xp=data.displacement,
    #             convertfunc=lambda x: x*details.gauge.value)
    #
    # set_secondary_label(ax1, xx=data.stress, xp=data.load, ax_dir='y', side='right',
    #             convertfunc=lambda x: x*details.measurements.area.value, position=('outward',0))
        
    return fig, axes, calc

def handler(testinfo:TestInfo, testfolder:FileStructure, details:DataTree, testdata:DataTree, args:DataTree):
    
    csvdata = testdata.tests.cycles.trends
    
    # debug('cycle_trends',displayjson(details.summaries))
    
    balances = DataTree()
    data = data_configure_load(testinfo=testinfo, data=csvdata, details=details, 
                                data_kind='trends', 
                                balances=details.summaries.step04_cycles )
    
    data.elapsedCycles = csvdata.elapsedCycles
    data.balances = DataTree(disp=DataTree(),load=DataTree())
    
    
    # data.balances.stress.summary = details.summaries.stress.summary['2.0']
    # data.balances.stress.offset = data.balances.stress.summary.mean
    #
    # data.balances.strain.summary = details.summaries.strain.summary['2.0']
    # data.balances.strain.offset = data.balances.strain.summary.mean
    
    # debug( dictdisplay(details) )
    
    # data.balances.disp.summary = ['step04_cycles','step_2','disp']
    # data.balances.disp.offset = details.summaries.step04_cycles.disp.summary['step_2'].mean
    #
    # data.balances.load.summary = ['step04_cycles','step_2','load']
    # data.balances.load.offset = details.summaries.step04_cycles.load.summary['step_2'].mean
    
    data.summaries = DataTree()
    
    updated = lambda d1,d2: [ d1.summaries[k].update(v) for k,v in d2.items() ]
    
    data.update( data_normalize(testinfo, data, details, suffix='max') )
    data.update( data_normalize(testinfo, data, details, suffix='min') )
    
    # debug(data.summaries.keys())
    
    # debug( dictdisplay(data.summaries) )
    
    fig, ax, calc = graph(testinfo=testinfo, testdata=data, testdetails=details, testargs=args)
    # plt.show(block=True)
    testfolder.save_graph(name='cycle_trends', fig=fig)
    plt.close()
    
    testfolder.save_calculated_json(name='stresslevels', data=calc)
    
    return {}

def graphs2_handler(testinfo, testfolder, testdata, args, **kwargs):
    
    return handler(testinfo, testfolder, details=testdata.details, testdata=testdata, args=args, )    

    
if __name__ == '__main__':
    
    import scilab.graphs.graph_runner2
    scilab.graphs.graph_runner2.main()

