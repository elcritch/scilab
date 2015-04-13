#!/usr/bin/env python3

import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

from scilab.tools.project import *
import numpy as np

def find_index(t, times):
    for i, tau in enumerate(times):
        if t < tau:
            return i

def graph(test, matdata, args, zconfig=DataTree(), **graph_opts):

    # if zconfig['item'] != "tracking":
    #     return DataTree()

    data, colinfo, indexes = matdata.data, matdata.columninfo, matdata.indexes
    
    if not (zconfig == DataTree(stage='norm', method='m3_cycles', item='trends')):
        print("WARNING::Graph doesn't match graph type: "+repr(zconfig))
        return DataTree()
    
    stepslice = slice(*matdata.indexes.step.idx_5)
    debug([ matdata.indexes.step.idx_5 ])
    
    getfield = lambda n: ( getattr(matdata.data, n)[stepslice], getattr(matdata.columninfo, n) )
    t,tl = getfield("totalCycles")
    # xmax,xmaxl = getfield("stress_max")
    ymax,ymaxl = getfield("strain_max")
    # xmin,xminl = getfield("stress_min")
    ymin,yminl = getfield("strain_min")
    
    # debug(xmax, ymax)
    calcs = DataTree()
    calcs.cycle_failure = test.details.variables.m3_cycles.trends.norm.post.calcs03.cycle_failure
    calcs.cf_idx = find_index(calcs.cycle_failure.value, t)
    
    # xmax = DataTree(value=test.details.variables.uts.tracking.norm.post.strain_max_value)
    target_stress_level = test.details['excel']['other']['stress_level']
    
    # Define Helpers
    limiter = lambda v, d, oa=0.0,ob=0.0: ( (1.0-d)*(min(v)+oa),(1.0+d)*(max(v)+ob) )
    labeler = lambda x: "{label} [{units}]".format(label=x.label, units=x.units)
    
    ## Setup plot
    fig, axes = plt.subplots(ncols=1, figsize=(14,6))
    ax1 = axes
    # ax2 = ax1.twinx()
    
    ## First Plot ##
    ax1.plot(t, ymax, label=ymaxl.label)
    ax1.set_xlabel(labeler(tl))
    ax1.set_ylabel(labeler(ymaxl))
    ax1.set_xscale('log')
    # ax2.set_ylabel(labeler(ymaxl))
    # ax1.set_ylim((-0.10*other.uts_stress.value, 1.2*other.uts_stress.value))
    
    ax1.scatter(t[calcs.cf_idx], ymax[calcs.cf_idx], 
        label="Failure Cycles (%d %s)"%(int(calcs.cycle_failure.value),calcs.cycle_failure.units))
    
    ax1.legend(loc=2, fontsize=10)
    fig.suptitle("Strain vs Log Cycles")
    
    
    # for idx in indexes.step._fieldnames:
    #     sl = getattr(indexes.step, idx)
    #     debug(idx, sl)
    #     ax1.axvline(t[sl[0]], *ax1.get_ybound(), color='purple')
        
    
    # ## y2 Plot ##
    # ax2.plot(t, ymax, color='darkgrey', label=yl.label)
    # ax2.legend(loc=1, fontsize=10)
    
    # set_secondary_label(ax1, xx=stress.strain, xp=data.displacement,
    #             convertfunc=lambda stress: x*details.gauge.value)
                
    return DataTree(fig=fig, axes=axes, calcs=DataTree())
