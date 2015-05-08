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

    if not ("norm" in zconfig["stage"] and "cycles" in zconfig["method"] and "trends" in zconfig["item"]):
        print("WARNING::Graph doesn't match graph type: "+repr(zconfig))
        return DataTree()
    
    stepslice = slice(*matdata.indexes.step.idx_5)
    debug([ matdata.indexes.step.idx_5 ])
    
    getfield = lambda n: ( getattr(matdata.data, n)[stepslice], getattr(matdata.columninfo, n) )
    t,tl = getfield("cycleStartTime")
    xmax,xmaxl = getfield("stress_max")
    xmin,xminl = getfield("stress_min")
    xamp,xampl = getfield("stress_amp")
    ymax,ymaxl = getfield("strain_max")
    ymin,yminl = getfield("strain_min")
    yamp,yampl = getfield("strain_amp")
    debug(xmax, ymax)
    
    # xmax = DataTree(value=test.details.variables.uts.tracking.norm.post.strain_max_value)
    target_stress_level = test.details['excel']['other']['stress_level']
    
    # Define Helpers
    limiter = lambda v, d, oa=0.0,ob=0.0: ( (1.0-d)*(min(v)+oa),(1.0+d)*(max(v)+ob) )
    labeler = lambda x: "{label} [{units}]".format(label=x.label, units=x.units)
    
    other = test.details.excel.other
    calcs = DataTree()
    
    calcs.target_stress = test.details.variables.m3_cycles.trends.norm.post.calcs01.stress_peak_target
    calcs.stress_level = test.details.variables.m3_cycles.trends.norm.post.calcs01.stress_level_target
    calcs.pred_max_stress = test.details.variables.m3_cycles.trends.norm.post.calcs01.max_stress_predicted
    calcs.actual_stress = test.details.variables.m3_cycles.trends.norm.post.calcs02.stress_peak_actual
    calcs.actual_perc = test.details.variables.m3_cycles.trends.norm.post.calcs02.stress_level_actual
    calcs.stress_amp_target = test.details.variables.m3_cycles.trends.norm.post.calcs02.stress_amp_target
    calcs.stress_amp_actual = test.details.variables.m3_cycles.trends.norm.post.calcs02.stress_amp_actual
    calcs.stress_amp_percent = test.details.variables.m3_cycles.trends.norm.post.calcs03.stress_amp_percent
    calcs.load_balance = test.details["variables"]['m3_cycles']['tracking']['norm']['pre']['load_balance']['value'] / test.details.measurements.specimen.area.value
    
    ## Setup plot
    fig, axes = plt.subplots(ncols=2, figsize=(14,6))
    (ax1,ax2) = axes
    
    ## First Plot ##
    ax1.set_ylim((-0.10*calcs.pred_max_stress.value, 1.2*calcs.pred_max_stress.value))
    
    ax1_title = "%s vs %s"%(xmaxl.label, tl.label)
    ax1.plot(t, xmax, label=labeler(xmaxl))
    ax1.plot(t, xmin, label=labeler(xminl))
    
    ax1.set_xlabel(labeler(tl))
    ax1.set_ylabel(labeler(xmaxl))
    
    ax12 = ax1.twinx()
    ax12.set_ylim((-0.10*calcs.pred_max_stress.value, 1.2*calcs.pred_max_stress.value))
    
    
    # stress_max = .stress_max.mean
    
    avg_label='Avg. {:3.1f}±{:.2f} {} ({:.0f}%)'.format(calcs.actual_stress.value, calcs.actual_stress.stdev, calcs.actual_stress.units, calcs.actual_perc.value)
    tgt_label='Tgt. {:3.1f} (SL{})'.format(calcs.target_stress.value, calcs.stress_level.value)
    pred_label='PredMax. {:3.1f} (SL{})'.format(calcs.pred_max_stress.value, calcs.stress_level.value)
    
    ax12.hlines(calcs.load_balance, *ax1.get_xbound(), linestyles='dotted', label='Offset', color='black')
    ax12.hlines(calcs.actual_stress.value, *ax1.get_xbound(), linestyles='dashed', label=avg_label, color='black')
    ax12.hlines(calcs.target_stress.value, *ax1.get_xbound(), linestyles='dashed', label=tgt_label, color='orange')
    ax12.hlines(calcs.pred_max_stress.value, *ax1.get_xbound(), linestyles='dashed', label=pred_label, color='red')
    
    ax1.legend(loc=0, fancybox=True, framealpha=0.0, )
    ax12.legend(loc=3, fancybox=True, framealpha=0.0, )
    ax1.set_title(ax1_title)
    
    # === Second Plot ===
    ax2_title = "%s vs %s"%(xampl.label, tl.label)
    
    ax2.plot(t, xamp, label=labeler(xampl), color=next(ax1._get_lines.color_cycle))
    
    ax2.set_xlabel(labeler(tl))
    ax2.set_ylabel(labeler(xampl))

    ax2.set_ylim((-0.10*calcs.pred_max_stress.value, 1.2*calcs.pred_max_stress.value))

    avg_label='Avg. {:3.1f}±{:.2f} {} ({:.0f}%)'.format(calcs.stress_amp_actual.value, calcs.stress_amp_actual.stdev, calcs.stress_amp_actual.units, calcs.stress_amp_percent.value)
    tgt_label='Tgt. {:3.1f} (SL{})'.format(calcs.stress_amp_target.value, calcs.stress_level.value)

    ax2.hlines(calcs.stress_amp_actual.value, *ax1.get_xbound(), linestyles='dashed', color='black', label=avg_label)
    ax2.hlines(calcs.stress_amp_target.value, *ax1.get_xbound(), linestyles='dashed', color='orange', label=tgt_label)

    ax3 = ax2.twinx()
    ax3.plot(t, yamp, label=labeler(xampl), color=next(ax1._get_lines.color_cycle), ls='-') 
    ax3.set_ylabel(labeler(yampl))
    
    # ax2.hlines(target_disp_level.value, *ax2.get_xbound(), linestyles='dashed', label='Targ. '+ymaxl.label)
    
    ax2.legend(loc=0, fontsize=10,fancybox=True, framealpha=0.5)
    ax3.legend(loc=1, fontsize=10,fancybox=True, framealpha=0.5)
    ax2.set_title(ax2_title)
    fig.subplots_adjust(hspace=1.4, )    
    # Make some room at the bottom 
    fig.subplots_adjust(bottom=0.20, left=0.20, right=0.80, top=0.90)
    
    return DataTree(fig=fig, axes=(ax1,ax2), calcs=DataTree())

    

