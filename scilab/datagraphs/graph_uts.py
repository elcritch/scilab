#!/usr/bin/env python3
import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

from scilab.tools.project import *
import numpy as np
import scilab.tools.fitting as Fitting

def graph(test, matdata, args, step_idx='idx_2', zconfig=DataTree(), **graph_args):

    if not (zconfig["stage"] =='norm' and "uts" in zconfig["method"] and "tracking" in zconfig["item"]):
        logging.warning("Graph doesn't match graph type: "+repr(zconfig))
        return DataTree()
    
    
    getfield = lambda n: ( getattr(matdata.data, n), getattr(matdata.columninfo, n) )
    t,tl = getfield("totalTime")
    x,xl = getfield("strain")
    y,yl = getfield("stress")
    xmax = DataTree(value=test.details.variables.uts.tracking.norm.post.strain_max_value)
    ymax = test.details.variables.uts.tracking.norm.post.stress_max 
    
    
    # Define Helpers
    limiter = lambda v, d, oa=0.0,ob=0.0: ( (1.0-d)*(min(v)+oa),(1.0+d)*(max(v)+ob) )
    labeler = lambda x: "{label} [{units}]".format(label=x.label, units=x.units)

    ax1_title = "UTS %s vs %s"%(labeler(xl), labeler(yl))
    
    fig, (ax1,ax2) = plt.subplots(ncols=2, figsize=(14,6))    
    # ax2 = ax1.twinx() # <http://stackoverflow.com/questions/14762181/adding-a-y-axis-label-to-secondary-y-axis-in-matplotlib>

    # First Plot
    ax1.plot(x, y, label=yl.label)
    ax1.set_xlabel(labeler(xl))
    ax1.set_ylabel(labeler(yl))
    
    load_offset = test.details.variables.precond.tracking.norm.pre.load_balance
    loadbalance = -load_offset.value/test.details.measurements.specimen.area.value
    ax1.hlines(loadbalance, x[0],x[-1], linestyles='dashed')
        
    uts_label = "UTS: (%.2f, %.2f) [%s,%s]"%(ymax.value, x[ymax.idx], yl.units, xl.units, )
    uts_peak = (x[ymax.idx], ymax.value)
    
    ax1.set(xlim=limiter(x, 0.08), ylim=limiter(y, 0.08,oa=loadbalance))
    
    ax1.scatter(uts_peak[0], uts_peak[1])
    
    ax1.annotate(uts_label, xy=uts_peak, xytext=(+30, -20), 
                    bbox=dict(boxstyle="round", fc="0.9"),
                    textcoords='offset points', 
                    fontsize=12,
                    arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"),
                    )

    debug(uts_label)
    
    ax1.legend(loc=0, fontsize=10)
    ax1.set_title(ax1_title)
    
    # Strain plot
    
    # Second Plot
    ax2.plot(t, x, label=labeler(xl))
    ax2.plot(t, y, label=labeler(yl))
    ax2.set_xlabel(labeler(tl))

    ax2.legend(loc=0,fontsize=10, )
    ax2.set_title("Individual Channels")

    # fig.tight_layout()
    # fig.text(.45, .95, testinfo.name)
    fig.suptitle('UTS Failure: '+str(test.info.short))

    def legend_handles(ax, x=0.5, y=-0.1):
        handles, labels = ax.get_legend_handles_labels()
        lgd = ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(x,y))
        return lgd
    
    # lgd1 = legend_handles(ax1, x=.1)
#     lgd1 = None
#     lgd2 = legend_handles(ax2, x=.9)
    
    fig.subplots_adjust(hspace=1.4, )
    
    # Make some room at the bottom
    fig.subplots_adjust(bottom=0.20, left=0.20, right=0.80, top=0.90)

    def set_labels(axes, xx, xp, ax_dir='x',side='bottom', 
                    convertfunc=lambda x: 1.0*x, position=('outward',40)):
        ax1twiny = axes.twiny() if ax_dir=='x' else axes.twinx()

        Gax1twiny = lambda s: getattr(ax1twiny, s.format(x=ax_dir))
        Gaxes = lambda s: getattr(axes, s.format(x=ax_dir))

        oldaxvalues = np(Gaxes('get_{x}ticks')())
        oldbounds = np(Gaxes('get_{x}lim')())
        newbounds = convertfunc(oldbounds)
        # ax1Xlabels = np(Gax1twiny('get_{x}ticklabels')())
        # ax1Idxs = xx.searchsorted(ax1Xs)
        # ticks_cycles = np.linspace(newbounds[0], newbounds[-1], len(ax1Xs))
        ticks_cycles = convertfunc(oldaxvalues)
        # debug(ticks_cycles, oldbounds, newbounds, oldaxvalues)
        # debug(ax_dir, xx[::100], ax1Xs, ax1Idxs, ax1Xs.shape, xp.shape, ticks_cycles)

        Gax1twiny('set_{x}ticks')      ( ticks_cycles )
        Gax1twiny('set_{x}bound')      ( newbounds )
        Gax1twiny('set_{x}ticklabels') ( [ "{:.0f}".format(i) for i in ticks_cycles ], rotation='vertical')
        Gax1twiny('set_{x}label')      ( labeler(xpl)+' [%s]'%xp.units)

        Gax1twiny('set_frame_on')(True)
        Gax1twiny('patch').set_visible(False)
        Gax1twiny('{x}axis').set_ticks_position(side)
        Gax1twiny('{x}axis').set_label_position(side)
        Gax1twiny('spines')[side].set_position(position)

    #set_labels(ax1, xx=matdata.data.disp, xp=matdata.data.strain, 
    #            convertfunc=lambda x: x/test.details.gauge.value)

    #set_labels(ax1, xx=matdata.data.load, xp=matdata.data.stress, ax_dir='y', side='right',
    #            convertfunc=lambda x: x*details.measurements.area.value, position=('outward',0))
    
    return DataTree(fig=fig, axes=(ax1,ax2), calcs=DataTree())

