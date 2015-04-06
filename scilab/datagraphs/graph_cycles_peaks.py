#!/usr/bin/env python3
# coding: utf-8

import csv
import sys, os

from pylab import *
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator
import glob, logging

import scilab.tools.jsonutils as Json
from scilab.tools.project import *
from scilab.expers.configuration import *
from scilab.tools.instroncsv import *

from scilab.datahandling.datahandlers import *
import scilab.datahandling.columnhandlers as columnhandlers  
import scilab.utilities.merge_calculated_jsons as merge_calculated_jsons


def graph(test, matdata, args, step_idx='idx_5', zconfig=DataTree(), **graph_args):

    if not (zconfig == DataTree(stage='norm', method='m3_cycles', item='trends')):
        print("WARNING::Graph doesn't match graph type: "+repr(zconfig))
        return DataTree()
    
    stepslice = slice(*matdata.indexes.step.idx_5)
    debug([ matdata.indexes.step.idx_5 ])
    
    getfield = lambda n: ( getattr(matdata.data, n)[stepslice], getattr(matdata.columninfo, n) )
    t,tl = getfield("cycleStartTime")
    xmax,xmaxl = getfield("stress_max")
    ymax,ymaxl = getfield("strain_max")
    xmin,xminl = getfield("stress_min")
    ymin,yminl = getfield("strain_min")
    
    debug(xmax, ymax)
    
    # xmax = DataTree(value=test.details.variables.uts.tracking.norm.post.strain_max_value)
    target_stress_level = test.details['excel']['other']['stress_level']
    
    # Define Helpers
    limiter = lambda v, d, oa=0.0,ob=0.0: ( (1.0-d)*(min(v)+oa),(1.0+d)*(max(v)+ob) )
    labeler = lambda x: "{label} [{units}]".format(label=x.label, units=x.units)

    
    other = test.details.excel.other
    calcs = DataTree()
    
    calcs.target_stress = valueUnits(other.test_max_force.value / test.details.measurements.datasheet.area.value, 'MPa')
    calcs.stress_level = int(100*other.stress_level.value)
    calcs.pred_max = other.uts_stress # *test.details.measurements.area.value
    calcs.actual = valueUnits(xmax.mean(), units=xmaxl.units)
    calcs.actual_perc = valueUnits(calcs.actual.value/(calcs.pred_max.value) * 100.0, '%')
    calcs.load_balance = 0.0
    calcs.precond_disp = other.precond_disp
    
    target_disp_level = calcs.precond_disp
    
    ## Setup plot
    fig, axes = plt.subplots(ncols=2, figsize=(14,6))
    (ax1,ax2) = axes
    
    ## First Plot ##
    ax1_title = "%s vs %s"%(xmaxl.label, tl.label)
    ax1.plot(t, xmax)
    ax2.set_xlabel(labeler(tl))
    ax2.set_ylabel(labeler(xmaxl))
    
    # stress_max = .stress_max.mean
    ax1.hlines(-calcs.load_balance, *ax1.get_xbound(), linestyles='dashed', label='Offset', color='lightgrey')
    
    avg_label='Avg. {:3.1f} ({:.0f}%)'.format(calcs.actual.value, calcs.actual_perc.value)    
    tgt_label='Tgt. {:3.1f} (SL{})'.format(calcs.target_stress.value, calcs.stress_level)
    pred_label='PredMax. {:3.1f} (SL{})'.format(calcs.pred_max.value, calcs.stress_level)
    
    ax1.hlines(calcs.actual.value, *ax1.get_xbound(), linestyles='dashed', label=avg_label, color='black')
    ax1.hlines(calcs.target_stress.value, *ax1.get_xbound(), linestyles='dashed', label=tgt_label, color='orange')
    ax1.hlines(calcs.pred_max.value, *ax1.get_xbound(), linestyles='dashed', label=pred_label, color='red')
    
    # label_stress_max = "Stress Peak Avg: {:.2f} [{}]".format(x[y.summary.maxs.idx], x.units, )
    # debug(label_stress_max)
    # graph_annotation_data(ax1, label_stress_max, xy=uts_peak,)
    
    # ax1.set(xlim=limiter(t, 0.08), ylim=limiter(x, 0.8))
    ax1.legend(loc=3, fancybox=True, framealpha=0.0, )
    ax1.set_title(ax1_title)
    
    ## Second Plot ##
    
    ax2_title = "%s vs %s"%(ymaxl.label, tl.label, )
    
    ax2.plot(t, ymax)
    ax2.set_xlabel(labeler(tl))
    ax2.set_ylabel(labeler(ymaxl))
    
    ax2.hlines(target_disp_level, *ax2.get_xbound(), linestyles='dashed', label='Targ. '+ymaxl.label)
    
    # ax2.set(xlim=limiter(t, 0.08), ylim=limiter(y, 0.08))
    ax2.legend(loc='best', fontsize=10,fancybox=True, framealpha=0.5)
    ax2.set_title(ax2_title)

    fig.subplots_adjust(hspace=1.4, )
    
    # Make some room at the bottom 
    fig.subplots_adjust(bottom=0.20, left=0.20, right=0.80, top=0.90)
            
    return DataTree(fig=fig, axes=(ax1,ax2), calcs=DataTree(cycles=calcs))

    

