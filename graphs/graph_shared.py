#!/usr/bin/env python3

import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

from scilab.tools.project import *
import scilab.tools.scriptrunner as ScriptRunner
from scilab.tools.instroncsv import csvread
import scilab.tools.json as Json
import scilab.tools.project as Project
import scilab.tools.graphing as Graphing
from scilab.tools.graphing import DataMax
import numpy as np


PlotData = namedtuple('PlotData', 'array label units')

from scilab.expers.configuration import FileStructure, TestInfo, TestData, TestDetails

# from addict import Dict 

limiter = lambda v, d, oa=0.0,ob=0.0: ( (1.0-d)*(min(v)+oa),(1.0+d)*(max(v)+ob) )
labeler = lambda x: "{label} [{units}]".format(**x.__dict__)

def get_max(data):
    idx, value = np.argmax(data)
    return DataTree(idx=idx, value=value)

def get_min(data):
    idx, value = np.argmin(data)
    return DataTree(idx=idx, value=value)

def data_find_max(data):
    idx = np.argmax(data)
    return DataMax(idx=idx, value=data[idx], name=None)

def data_configure_load(testinfo:TestInfo, data:DataTree, details:DataTree, cycles=False, trends=False):
    
    updated = DataTree()
    
    if 'load' in data:
        return updated

    if cycles:
        if testinfo.orientation == 'tr':
            loads = [ l for l in ['loadLinearMissus','loadLinearLoad1'] if l in data ]
        if testinfo.orientation == 'lg':
            loads = [ l for l in ['loadLinearLoad'] if l in data ]
        
        logging.warn("Choosing loads: "+repr(loads))
        updated.load = data[loads[0]]
    
    if trends:
        if testinfo.orientation == 'tr':
            if 'load_max' not in data:
                load_max = data.loadLinearLoad1Maximum # choose Honeywell
            if 'load_min' not in data:
                load_min = data.loadLinearLoad1Minimum # choose Honeywell
        if testinfo.orientation == 'lg':
            if 'load_max' not in data:
                load_max = data.loadLinearLoad1Maximum # choose 1kN
            if 'load_min' not in data:
                load_min = data.loadLinearLoad1Minimum # choose 1kN
        
        if 'disp_max' not in data:
            disp_max = data.displacementLinearDigitalPositionMaximum # choose peak disp
        if 'disp_min' not in data:
            disp_min = data.displacementLinearDigitalPositionMinimum # choose peak disp
        
        updated.load_max = load_max
        updated.load_min = load_min
        updated.disp_max = disp_max
        updated.disp_min = disp_min
        
    if not updated:
        raise ValueExceptioN("Choose something!")

    return updated


def data_stepsummaries(testinfo:TestInfo, data:DataTree, details:DataTree):
    
    def summaryvalues(val, sl):
        xx = val.array[sl]
        return DataTree(mean=xx.mean(),std=xx.std(),mins=get_min(xx),maxs=get_max(xx))

    # stepslice = data._getslices('step')[1]
    stepsummaries = DataTree()
    stepslices = list(data._getslices('step').items()) + [(-1, np.s_[0,-1,] ), ]
    
    for key, stepslice in stepslices:
        summary = DataTree()
        summary.slice = stepslice
        summary.load =  summaryvalues(data.load, stepslice)
        summary.disp =  summaryvalues(data.displ, stepslice)
        summary.load_peak_disp = DataTree(idx=summary.load.maxs.idx, 
                                          value=data.disp.array[summary.load.maxes.idx])
        
        summary.stress =  summaryvalues(data.stress, stepslice)
        summary.strain =  summaryvalues(data.strain, stepslice)
        summary.stress_peak_strain = DataTree(idx=summary.stress.maxs.idx, 
                                          value=data.strain.array[summary.stress.maxes.idx])
        
        stepsummaries[key] = summary

    stepsummaries.balance = DataTree()
    stepsummaries.balance.balancestep = balancestep
    stepsummaries.balance.offset_load = DataTree(load=stepsinfo.balance.load.mean)
    stepsummaries.balance.offset_stress = DataTree(load=stepsinfo.balance.stress.mean)

    return {'stepsummaries':stepsummaries}

def data_normalized(testinfo:TestInfo, data:DataTree, details:DataTree, 
                    loadname='load', dispname='disp',suffix="",
                    stressname='Stress', strainname='Strain',
                    stressunits='MPa', strainunits='∆',
                    ):

    if suffix:
        loadname += '_' + suffix
        dispname += '_' + suffix
        stressname += '_' + suffix
        strainname += '_' + suffix
    
    debug(suffix, loadname)
    normalized = DataTree()
    # data.load_orig = data.load
    normalized[loadname] = PlotData(array=data[loadname].array - data.stepsummaries.balance.offset,
                               label=data[loadname].label, units=data[loadname].label)
    
    strain = data[dispname].array / details.gauge.value
    stress = data[loadname].array / details.measurements.area.value
    
    normalized[stressname.lower()] = PlotData(array=stress, label=stressname, units=stressunits)
    normalized[strainname.lower()] = PlotData(array=strain, label=strainname, units=strainunits)

    return normalized

def data_sliced(testinfo:TestInfo, data:DataTree, details:DataTree, step, cols=['load', 'disp', 'strain', 'stress']):

    datasliced = DataTree()
    
    sl_ = data._getslices('step')[step]
    
    for d in [ data[c] for c in cols if c in data ]:
        datasliced[col] = PlotData(array=d.array[sl_], label=d.label, units=d.units)
        
    return datasliced
        
def graph_annotation_data(ax, label, xy, xytext=(+30, -20)):
    
    ax.annotate(label, xy=xy, xytext=xytext, 
                    bbox=dict(boxstyle="round", fc="0.9"),
                    textcoords='offset points', 
                    arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"),
                    )
    return
    

    
def set_secondary_label(axes, xx, xp, ax_dir='x',side='bottom', tickfmt = "{:.0f}",
                        convertfunc=lambda x: 1.0*x, position=('outward',40)):
    axtwins = axes.twiny() if ax_dir=='x' else axes.twinx()

    Gaxtwin = lambda s: getattr(axtwins, s.format(x=ax_dir))
    Gaxes = lambda s: getattr(axes, s.format(x=ax_dir))
    
    oldaxvalues = np.array(Gaxes('get_{x}ticks')())
    oldbounds = np.array(Gaxes('get_{x}lim')())
    newbounds = convertfunc(oldbounds)
    
    # ax1Xlabels = np.array(Gaxtwin('get_{x}ticklabels')())
    # ax1Idxs = xx.array.searchsorted(ax1Xs)
    # newticks = np.linspace(newbounds[0], newbounds[-1], len(ax1Xs))
    
    newticks = convertfunc(oldaxvalues)
    
    # debug(newticks, oldbounds, newbounds, oldaxvalues)
    # debug(ax_dir, xx.array[::100], ax1Xs, ax1Idxs, ax1Xs.shape, xp.array.shape, newticks)

    Gaxtwin('set_{x}ticks')      ( newticks )
    Gaxtwin('set_{x}bound')      ( newbounds )
    Gaxtwin('set_{x}ticklabels') ( [ tickfmt.format(i) for i in newticks ], rotation='vertical')
    Gaxtwin('set_{x}label')      ( xp.label+' [%s]'%xp.units)

    Gaxtwin('set_frame_on')(True)
    Gaxtwin('patch').set_visible(False)
    Gaxtwin('{x}axis').set_ticks_position(side)
    Gaxtwin('{x}axis').set_label_position(side)
    Gaxtwin('spines')[side].set_position(position)


