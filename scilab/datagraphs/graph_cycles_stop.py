#!/usr/bin/env python3

import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

from scilab.tools.project import *
import numpy as np
from matplotlib.ticker import MultipleLocator, FormatStrFormatter

def graph(test, matdata, args, zconfig=DataTree(), **graph_opts):

    # if zconfig['item'] != "tracking":
    #     return DataTree()

    data, colinfo, indexes = matdata.data, matdata.columninfo, matdata.indexes
    
    if not ("norm" in zconfig["stage"] and "cycles" in zconfig["method"] and "tracking" in zconfig["item"]):
        print("WARNING::Graph doesn't match graph type: "+repr(zconfig))
        return DataTree()
    
    stepslice = slice(-5000,-1,1)
    getfield = lambda n: ( getattr(matdata.data, n)[stepslice], getattr(matdata.columninfo, n) )

    t,tl = getfield("totalTime")
    tc,tcl = getfield("totalCycleCount")
    x,xl = getfield("stress")
    y,yl = getfield("strain")
    
    # === Define Helpers ===
    limiter = lambda v, d, oa=0.0,ob=0.0: ( (1.0-d)*(min(v)+oa),(1.0+d)*(max(v)+ob) )
    labeler = lambda x: "{label} [{units}]".format(label=x.label, units=x.units)
    
    # === Setup plot ===
    # fig, axes = plt.subplots(ncols=2, figsize=(14,6))
    # ax1 = axes[0]
    # ax2 = axes[1]
    
    ## Setup plot
    fig, axes = plt.subplots(ncols=1, figsize=(14,6))
    ax1 = axes
    ax2 = ax1.twinx()
    
    ## First Plot ##
    ax1.plot(t, x, label=xl.label)
    ax1.set_xlabel(labeler(tl))
    ax1.set_ylabel(labeler(xl))
    ax1.legend(loc=2, fontsize=10)
    
    # Twin x in cycles
    ax12 = ax1.twiny() 
    minorLocator   = MultipleLocator(1)
    majorLocator   = MultipleLocator(10)
    ax12.xaxis.set_major_locator(majorLocator)
    ax12.xaxis.set_minor_locator(minorLocator)
    
    ax12.plot(tc, tc*0)
    ax12.set_xlabel(labeler(tcl))
    
    
    # fig.suptitle("Overview All: {} ({})".format(test.info.short, repr(zconfig)))
    
    # === Y2 Plot ===
    ax2.plot(t, y, color='darkgrey', label=yl.label)
    ax2.set_ylabel(labeler(yl))
    ax2.legend(loc=1, fontsize=10)
    
    ax1.set_xlim(min(t), max(t))
    ax12.set_xlim(min(tc), max(tc))
    ax12.patch.set_visible(False)
    
    # === Titles === 
    fig.suptitle("Fatigue Cycle -- Final Cycles".format(test.info.short, repr(zconfig)))
    
    return DataTree(fig=fig, axes=axes, calcs=DataTree())
