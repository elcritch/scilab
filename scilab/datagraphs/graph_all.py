#!/usr/bin/env python3

import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

from scilab.tools.project import *
import numpy as np

def graph(test, matdata, args, zconfig=DataTree(), **graph_opts):

    data, info, indexes = matdata.data, matdata.columninfo, matdata.indexes
    
    if zconfig['stage'] == "norm":
        t, y, x = data.totalTime, data.stress, data.strain
        info_t, info_x, info_y = info.totalTime, info.stress, info.strain
    else:
        t, y, x = data.totalTime, data.load, data.disp
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
        debug(idx, sl)
        ax1.axvline(t[sl[0]], *ax1.get_ybound(), color='purple')
        
    
    ## y2 Plot ##
    ax2.plot(t, y, color='darkgrey', label=info_y.label)
    ax2.legend(loc=1, fontsize=10)
    
    # set_secondary_label(ax1, xx=stress.strain, xp=data.displacement,
    #             convertfunc=lambda stress: x*details.gauge.value)
                
    return DataTree(fig=fig, axes=axes, calcs=DataTree())
