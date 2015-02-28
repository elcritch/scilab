#!/usr/bin/env python3

import sys, os, glob, logging, collections
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0,[ str(p) for p in Path('.').resolve().parents if (p/'scilab').exists() ][0] )

from scilab.tools.project import *
import scilab.tools.scriptrunner as ScriptRunner
from scilab.tools.instroncsv import csvread
from scilab.tools.instroncsv import InstronColumnSummary, InstronColumnBalance
import scilab.tools.jsonutils as Json
import scilab.tools.project as Project
import scilab.tools.graphing as Graphing
from scilab.tools.graphing import DataMax
import numpy as np


# PlotData = namedtuple('PlotData', 'array label units')

from scilab.expers.configuration import *

# from addict import Dict 

limiter = lambda v, d, oa=0.0,ob=0.0: ( (1.0-d)*(min(v)+oa),(1.0+d)*(max(v)+ob) )
labeler = lambda x: "{label} [{units}]".format(label=x.label, units=x.label)
displayjson = lambda x: '\n'+'\n'.join([ "> .... {} -> {}".format(k,v) for k,v in flatten(x,sep='.').items() ])

def get_max(data):
    if not len(data):
        return DataTree(idx=None, value=None)
    idx = np.argmax(data)
    return DataTree(idx=idx, value=data[idx])

def get_min(data):
    if not len(data):
        return DataTree(idx=None, value=None)
    idx = np.argmin(data)
    return DataTree(idx=idx, value=data[idx])

def data_configure_load(testinfo:TestInfo, data:DataTree, details:DataTree, data_kind, 
                        balances=DataTree(),balancestep=None):
    
    assert data_kind in ['tracking', 'trends']
    
    updated = DataTree()
    updated.summaries = DataTree()
    
    dataconfig = DataTree(
        loadname='load', dispname='disp',suffix="",
        stressname='stress', strainname='strain',
        stressunits='MPa', strainunits='∆',
        )
    
    updated.config = dataconfig
    updated.steps = data._getslices('step')
    updated.steps['step_all'] = np.s_[0:-1]
    print("Steps:",updated.steps)
    
    if 'load' in data:
        return updated

    if data_kind == 'tracking':
        if testinfo.orientation == 'tr':
            loads = [ l for l in ['loadLinearMissus','loadLinearLoad1'] if l in data ]
        if testinfo.orientation == 'lg':
            loads = [ l for l in ['loadLinearLoad'] if l in data ]
        
        logging.warn("Choosing loads: "+repr(loads))
        updated.load = data[loads[0]]
        updated.disp = data.displacement
        updated.summaries.update(data_datasummaries(
            testinfo, updated, details,
            balancestep=balancestep, balances=balances,
            cols=[dataconfig.loadname, dataconfig.dispname]))

    elif data_kind == 'trends':
        if testinfo.orientation == 'tr':
            if 'load_max' not in data:
                load_max = data.loadLinearLoad1Maximum # choose Honeywell
            if 'load_min' not in data:
                load_min = data.loadLinearLoad1Minimum # choose Honeywell
        if testinfo.orientation == 'lg':
            if 'load_max' not in data:
                load_max = data.loadLinearLoadMaximum # choose 1kN
            if 'load_min' not in data:
                load_min = data.loadLinearLoadMinimum # choose 1kN
        
        if 'disp_max' not in data:
            disp_max = data.displacementLinearDigitalPositionMaximum # choose peak disp
        if 'disp_min' not in data:
            disp_min = data.displacementLinearDigitalPositionMinimum # choose peak disp
        
        updated.load_max = load_max
        updated.load_min = load_min
        updated.disp_max = disp_max
        updated.disp_min = disp_min
        
        updated.summaries.update(data_datasummaries(
            testinfo, updated, details, 
            balancestep=balancestep,
            balances=balances,
            cols=['load_max', 'load_min', 'disp_max', 'disp_min']) )
        
    if not updated:
        raise ValueExceptioN("Choose something!")

    return updated

# @debugger
def data_datasummaries( testinfo:TestInfo, 
                        data:DataTree, 
                        details:DataTree, 
                        balancestep=None,
                        balances=DataTree(),
                        cols=['load', 'disp']):
    
    datasummaries = DataTree()
    
    # debug('data_datasummaries', cols, balancestep)
    
    # if not balancestep:
        # raise Exception()
    
    assert not (balancestep and balances)
    
    @debugger
    def summaryvalues(val, sl):
        # debug(val.array.shape, sl)
        xx = val.array[sl]
        return InstronColumnSummary(mean=xx.mean(),std=xx.std(),mins=get_min(xx),maxs=get_max(xx))
    
    @debugger
    def summarize(colname):
        _summarize = lambda sl: summaryvalues(data[colname], sl).set(slices=sl)
        return DataTree({ key:_summarize(stepslice) for key, stepslice in data.steps.items() })
    
    @debugger
    def dobalances(colname, summary):
        # debug(summary)
        return InstronColumnBalance(step=balancestep, offset=summary[balancestep].mean)
        
        return balances
        
    for colname in cols:
        summary = summarize(colname)
        
        if colname in balances:
            balance = balances[colname]
        elif balancestep:
            balance = dobalances(colname, summary)
        else:
            balance = InstronColumnBalance(offset=0.0)
        
        datasummaries[colname] = DataTree(balance=balance,summary=summary)

    return datasummaries

def data_normalize_col(testinfo:TestInfo, data:DataTree, details:DataTree, 
                    normfactor, xname, yname, yunits, balance, 
                    ):

    normalized[yname] = DataTree(array=data[xname].array * normfactor.value, 
                                 label=yname.capitalize(), 
                                 units=yunits)

    normalized.summaries.update(data_datasummaries(testinfo, normalized, details, cols=[yname]))

    normalized.summaries[strainname].balance = normalized.summaries[dispname].balance * normfactor
    
    return normalized

def data_normalize(testinfo:TestInfo, data:DataTree, details:DataTree, 
                    loadname='load', dispname='disp',suffix="",
                    stressname='stress', strainname='strain',
                    stressunits='MPa', strainunits='∆',
                    ):

    if suffix:
        loadname += '_' + suffix
        dispname += '_' + suffix
        stressname += '_' + suffix
        strainname += '_' + suffix
    
    # debug(suffix, loadname)
    normalized = DataTree(steps=data.steps)
    
    normalized.summaries = DataTree(**data.summaries)
    normalized.summaries.update(data_datasummaries(testinfo, data, details, cols=[loadname, dispname]))
    
    # debug(displayjson(data.summaries), displayjson(normalized.summaries))
    # debug(list(data.keys()))
    # debug(displayjson(data.get('balance', {})), displayjson(data.get('balances', {})))
    # debug('data_normalize',displayjson(data.summaries))

    # normalized.summaries.load.summary.step_3.std
    load_balance = normalized.summaries[loadname]['balance']
    disp_balance = normalized.summaries[dispname]['balance']
    if load_balance:
        normalized.summaries[loadname].balance = load_balance
    if disp_balance:
        normalized.summaries[dispname].balance = disp_balance
    
    # data.load_orig = data.load
    
    offset_load = normalized.summaries[loadname].balance.offset if normalized.summaries[loadname].balance else 0.0
    normalized[loadname] = data[loadname].set(array=data[loadname].array-offset_load)
    normalized[dispname] = data[dispname]
    
    # pre=data_datasummaries(testinfo, data, details, cols=[loadname]),
    # post=data_datasummaries(testinfo, normalized, details, cols=[loadname]),
    # debug(pre, post)
    
    # DataTree(array=data[loadname].array - data.summaries[loadname].balance.offset,
                               # label=data[loadname].label, units=data[loadname].label)
    
    strain = data[dispname].array / details.gauge.value
    stress = data[loadname].array / details.measurements.area.value
    
    normalized[stressname] = DataTree(array=stress, label=stressname.capitalize(), units=stressunits)
    normalized[strainname] = DataTree(array=strain, label=strainname.capitalize(), units=strainunits)

    normalized.summaries.update(data_datasummaries(testinfo, normalized, details, cols=[strainname, stressname]))

    normalized.summaries[strainname].balance = normalized.summaries[dispname].balance
    normalized.summaries[stressname].balance = normalized.summaries[loadname].balance
    normalized.summaries[strainname].balance.offset /= details.gauge.value
    normalized.summaries[stressname].balance.offset /= details.measurements.area.value
    
    return normalized

def data_sliced(testinfo:TestInfo, data:DataTree, details:DataTree, step, cols=['load', 'disp', 'strain', 'stress']):

    datasliced = DataTree()
    
    sl_ = data.steps[step]
    
    for d in [ data[c] for c in cols if c in data ]:
        datasliced[col] = DataTree(array=d.array[sl_], label=d.label, units=d.units)
        
    return datasliced
        
def graph_annotation_data(ax, label, xy, xytext=(+30, -20)):
    
    ax.annotate(label, xy=xy, xytext=xytext, 
                    bbox=dict(boxstyle="round", fc="0.9"),
                    textcoords='offset points', 
                    arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"),
                    )
    return
    

    
def set_secondary_label(axes, label, ax_dir='x',side='bottom', tickfmt = "{:.0f}",
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
    Gaxtwin('set_{x}label')      ( label.label+' [%s]'%xp.units)

    Gaxtwin('set_frame_on')(True)
    Gaxtwin('patch').set_visible(False)
    Gaxtwin('{x}axis').set_ticks_position(side)
    Gaxtwin('{x}axis').set_label_position(side)
    Gaxtwin('spines')[side].set_position(position)

if __name__ == '__main__':
    
    import scilab.graphs.graph_runner2
    scilab.graphs.graph_runner2.main()

