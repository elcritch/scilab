#!/usr/bin/env python3

import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

from scilab.tools.project import *
import numpy as np

def graph(test, matdata, args, zconfig=DataTree(), **graph_opts):

    # if zconfig['item'] != "tracking":
    #     return DataTree()

    data, colinfo, indexes = matdata.data, matdata.columninfo, matdata.indexes
    
    getfield = lambda n: ( getattr(matdata.data, n), getattr(matdata.columninfo, n) )
    
    if "tracking" in zconfig["item"]:    
        if "norm" in zconfig["stage"]:
            t,tl = getfield("totalTime"); x,xl = getfield("stress"); y,yl = getfield("strain")
        else:
            t,tl = getfield("totalTime"); x,xl = getfield("load"); y,yl = getfield("disp")
    elif "trends" in zconfig["item"]:
        if "norm" in zconfig["stage"]:
            t,tl = getfield("cycleStartTime"); x,xl = getfield("stress_max"); y,yl = getfield("strain_max")
        else:
            t,tl = getfield("cycleStartTime"); x,xl = getfield("load_max"); y,yl = getfield("disp_max")
    
    limiter = lambda v, d, oa=0.0,ob=0.0: ( (1.0-d)*(min(v)+oa),(1.0+d)*(max(v)+ob) )
    labeler = lambda x: "{label} [{units}]".format(label=x.label, units=x.units)
    
    ## Setup plot
    fig, axes = plt.subplots(ncols=1, figsize=(14,6))
    ax1 = axes
    ax2 = ax1.twinx()
    
    ## First Plot ##
    ax1.plot(t, x, label=xl.label)
    ax1.set_xlabel(labeler(tl))
    ax1.set_ylabel(labeler(xl))
    ax2.set_ylabel(labeler(yl))
    
    ax1.legend(loc=2, fontsize=10)
    fig.suptitle("Test Sample: {}".format(test.info.short))
    
    for idx in indexes.step._fieldnames:
        sl = getattr(indexes.step, idx)
        debug(idx, sl)
        ax1.axvline(t[sl[0]], *ax1.get_ybound(), color='purple')
        
    
    ## y2 Plot ##
    ax2.plot(t, y, color='darkgrey', label=yl.label)
    ax2.legend(loc=1, fontsize=10)
    
    # set_secondary_label(ax1, xx=stress.strain, xp=data.displacement,
    #             convertfunc=lambda stress: x*details.gauge.value)
                
    return DataTree(fig=fig, axes=axes, calcs=DataTree())
