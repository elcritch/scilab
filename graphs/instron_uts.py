#!/usr/bin/env python3

import csv
import sys, os

from pylab import *
from scipy.stats import exponweib, weibull_max, weibull_min
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator
import glob, logging

from ntm.Tools.Project import *
from ntm.Tools.Graphing import DataMax

# from WaveMatrixToolsPy3 import *
from ntm.Tools.InstronCSV import csvread

import ntm.Tools.Project as Project
import ntm.Tools.Excel as Excel
import ntm.Tools.Graphing as Graphing 
import ntm.Tools.ScriptRunner as ScriptRunner
import ntm.Tools.Json as Json


PlotData = namedtuple('PlotData', 'array label units max')

def get_max(data):
    idx, value = np.argmax(data)
    return dict(idx=idx, value=value)

def data_find_max(data):
    idx = np.argmax(data)
    return DataMax(idx=idx, value=data[idx], name=None)

def handler(file_name, file_object, file_path, file_parent, args):
    
    data = csvread(file_path)
    data_json = Json.load_data(file_parent, file_name)    

    # json data
    details = data_json
    
    debug(data)
    data, details = data_cleanup_uts(data, details)
    
    print(" --------- \n")
    debug(data.maxes)
    
    maxes = {}
    for m,v in data.maxes.items():
        debug(m,v, type(v.idx))
        maxes[m] = {'idx':int(v.idx), 'value':v.value}
    
    debug(maxes)
    
    Json.update_data(file_parent, file_name, {'calculations': {'maxes':maxes} }, dbg=False )
    
    graph_uts_raw(file_name, file_parent, data, details, args)
    graph_uts_normalized(file_name, file_parent, data, details, args)
    

def data_cleanup_uts(data, details):

    if 'load' not in data.keys():
        data.load = data.loadLoad # choose Honeywell

    data.maxes = DataTree()
    data.maxes.displacement = data_find_max(data.displacement.array)
    data.maxes.load = data_find_max(data.load.array)
    
    
    debug(data.maxes)
    
    stress = data.load.array/details.measurements.area.value
    strain = data.displacement.array/details.gauge.length

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
    
def graph_uts_normalized(file_name, file_parent, data, details, args):
    
    t = makePlotData(data.totalTime, columnMax=None)
    x = makePlotData(data.strain, columnMax=data.maxes.strain)
    y = makePlotData(data.stress, columnMax=data.maxes.stress)
    
    graph_uts(file_name, file_parent, t, x, y, details, args)


def graph_uts_raw(file_name, file_parent, data, details, args):

    t = makePlotData(data.totalTime, columnMax=None)
    x = makePlotData(data.displacement, columnMax=data.maxes.displacement)
    y = makePlotData(data.load, columnMax=data.maxes.load)
        
    return graph_uts(file_name, file_parent, t, x, y, details, args)


def graph_uts(file_name, file_parent, t, x, y, details, args):
    
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
    fig.text(.45, .95, file_name)

    if args.only_first:
        plt.show(block=True,  )

    def legend_handles(ax, x=0.5, y=-0.1):
        handles, labels = ax.get_legend_handles_labels()
        lgd = ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(x,y))
        return lgd
    
    lgd1 = legend_handles(ax1, x=.1)
    lgd2 = legend_handles(ax2, x=.9)
    
    base_file_name = "%s (%s)"%(file_name[:file_name.index('.steps')], ax1_title)

    Graphing.fig_save(fig, os.path.join(file_parent, 'img'), name=base_file_name, type='.png', lgd=lgd1, lgd2=lgd2)
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
    # project = "Test4 - transverse fatigue (ntm-mf-pre)/trans-fatigue-trial1/"

    project = "Test4 - transverse fatigue (ntm-mf-pre)/test4(trans-uts)"
    fileglob = "{R}/{P}/*/*.tracking.csv".format(R=RAWDATA,P=project)
    
    test_args = ["--glob", fileglob] 
    test_args += ['-1'] # only first
    
    args = parser.parse_args( test_args)
    
    # Parse command line if not running test args.
    if 'args' not in locals():
        args = parser.parse_args()
    
    ScriptRunner.process_files_with(args=args, handler=handler)
    
    