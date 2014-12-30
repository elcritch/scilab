#!/usr/bin/env python3

import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator

from scilab.tools.project import *
import scilab.tools.scriptrunner as ScriptRunner
from scilab.tools.instroncsv import csvread
import scilab.tools.json as Json
import scilab.tools.project as Project
import scilab.tools.excel as Excel
import scilab.tools.graphing as Graphing
from scilab.tools.graphing import DataMax
import numpy as np

PlotData = namedtuple('PlotData', 'array label units max')

def get_max(data):
    idx, value = np.argmax(data)
    return dict(idx=idx, value=value)

def data_find_max(data):
    idx = np.argmax(data)
    return DataMax(idx=idx, value=data[idx], name=None)

def handler(test:Path, args:object):
    
    data = csvread(test)
    data_json = Json.load_data_path(test)    

    debug(data_json)

    # json data
    details = data_json
    
    debug(details)
    
    data, details = data_cleanup_uts(data, details)
    
    print(" --------- \n")
    debug(data.maxes)
    
    maxes = {}
    for m,v in data.maxes.items():
        debug(m,v, type(v.idx))
        maxes[m] = {'idx':int(v.idx), 'value':v.value}
    
    debug(maxes)
    
    Json.update_data_path(test, {'calculations': {'maxes':maxes} }, dbg=False )
    
    graph_uts_raw(test, data, details, args)
    graph_uts_normalized(test, data, details, args)
    

def data_cleanup_uts(data, details):

    if 'load' not in data.keys():
        loads = [ l for l in ['loadLinearMissus','loadLinearLoad'] if l in data ]
        logging.warn("Choosing loads: "+repr(loads))
        data.load = data[loads[0]]

    data.maxes = DataTree()
    data.maxes.displacement = data_find_max(data.displacement.array)
    data.maxes.load = data_find_max(data.load.array)
    
    
    debug(data.maxes)
    
    stress = data.load.array/details.measurements.area.value
    strain = data.displacement.array/details.gauge.value

    # hack    
    data.maxes.stress = data_find_max(stress)
    data.maxes.strain = data_find_max(strain)
    
    data.stress = PlotData(array=stress, label="Stress", units="MPa", max=None)
    data.strain = PlotData(array=strain, label="Strain", units="∆", max=None)
    
    if 'loadLinearLoad1' in data:
        stress1 = data.loadLinearLoad1.array/details.measurements.area.value
        data.stress1 = PlotData(array=stress1, label="Stress Honeywell", units="MPa", max=None)
        data.maxes.stress1 = data_find_max(stress1)
        data.maxes.loadLoad1 = data_find_max(data.loadLinearLoad1.array)
        
    return (data, details)

def makePlotData(column, columnMax=None):
    return PlotData(array=column.array, label=column.label, units=column.units, max=columnMax)
    
def graph_uts_normalized(testpath, data, details, args):
    
    t = makePlotData(data.totalTime, columnMax=None)
    x = makePlotData(data.strain, columnMax=data.maxes.strain)
    y = makePlotData(data.stress, columnMax=data.maxes.stress)
    
    graph_uts(testpath, t, x, y, details, args)


def graph_uts_raw(testpath, data, details, args):

    t = makePlotData(data.totalTime, columnMax=None)
    x = makePlotData(data.displacement, columnMax=data.maxes.displacement)
    y = makePlotData(data.load, columnMax=data.maxes.load)
        
    return graph_uts(testpath, t, x, y, details, args)


def graph_uts(test, t, x, y, details, args):
    
    ax1_title = "UTS %s vs %s"%(x.label, y.label)
    
    fig, (ax1,ax2) = plt.subplots(ncols=2, figsize=(14,6))
    # ax2 = ax1.twinx() # <http://stackoverflow.com/questions/14762181/adding-a-y-axis-label-to-secondary-y-axis-in-matplotlib>

    # First Plot
    ax1.plot(x.array, y.array)
    ax1.set_xlabel(x.label)
    ax1.set_ylabel(y.label)
    
    debug(y.max)
    uts_label = "UTS: %4.2f %s at %4.2f %s"%(y.max.value, y.units, x.array[y.max.idx], x.units, )
    ax1.plot(x.array[y.max.idx], y.max.value, 'or', label=uts_label)

    debug(uts_label)
    
    ax1.legend(loc=0, fontsize=10)
    ax1.set_title(ax1_title)
    
    # Second Plot
    ax2.plot(t.array, x.array, label=x.label+' '+x.units)
    ax2.plot(t.array, y.array, label=y.label+' '+y.units)
    ax2.set_xlabel(t.label)

    ax2.legend(loc=0,fontsize=10, )
    ax2.set_title("Individual Channels")

    # fig.tight_layout()
    fig.text(.45, .95, test.name)

    if args.only_first:
        plt.show(block=True,  )

    def legend_handles(ax, x=0.5, y=-0.1):
        handles, labels = ax.get_legend_handles_labels()
        lgd = ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(x,y))
        return lgd
    
    lgd1 = legend_handles(ax1, x=.1)
    lgd2 = legend_handles(ax2, x=.9)
    
    base_file_name = "%s (%s)"%(test.stems(), ax1_title)
    imgpath = test.parent / 'img'
    
    debug(base_file_name, imgpath)
    
    Graphing.fig_save(fig, str(imgpath), name=base_file_name, type='.png', lgd=lgd1, lgd2=lgd2)
    # Graphing.fig_save(fig, os.path.join(file_parent, 'img', 'eps'), name=base_file_name, type='.eps', lgd=lgd1, lgd2=lgd2)
    
    plt.close()
    
    return

if __name__ == '__main__':

    parser = ScriptRunner.parser
    
    parser.add_argument("-n", "--name", default="data", type=str)
    parser.add_argument("--raw", action='store_true', default=True, help="Run raw ", )  
    parser.add_argument("--normed", action='store_true', default=False,help="Run normalized ", )  

    ## Test
    # project = "NTM-MF-PRE (test4, trans, uts)"
    # project = "Test4 - transverse fatigue (scilab.mf.pre)/trans-fatigue-trial1/"

    projectname = 'NTM-MF/fatigue-failure-expr1/'
    projectpath = Path(RAWDATA) / projectname
    
    trackingfiles = projectpath.glob('04*/*/*.tracking.csv')
    
    test_args = [] 
    # test_args += ["--glob", fileglob]
    # test_args += ['-1'] # only first
    
    args = parser.parse_args( test_args)
    
    # Parse command line if not running test args.
    if 'args' not in locals():
        args = parser.parse_args()
    
    for trackingtest in list(trackingfiles)[:]:
        
        debug(trackingtest)
        
        handler(trackingtest, args=args)
        # def handler(testname:str, testdata:dict, args:object):
        
    # ScriptRunner.process_files_with(args=args, handler=handler)
    