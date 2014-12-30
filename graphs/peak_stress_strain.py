#!/usr/bin/env python3
# coding: utf-8

import csv
import sys, os

from pylab import *
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator
import glob, logging

from ..tools.project import *
from ..tools.graphing import *
from ..tools.instroncsv import *

from ..tools import project, excel, graphing, scriptrunner, json

PlotData = namedtuple('PlotData', 'array label units max')


def get_max(data):
    idx, value = np.argmax(data)
    return dict(idx=idx, value=value)

def data_find_max(name, data):
    idx = np.argmax(data)
    return DataMax(idx=idx, value=data[idx], name=name)

    handler(file=file,file_object=file_obect, args=args)
    
    all_data = csvread(file_path)
    data_json = Json.load_data_path(file)    

    debug(all_data.keys())
    
    indicies = all_data._getslices('step')
    
    all_data, details = data_cleanup_uts(all_data, data_json)

    
    # steps    
    # graph_raw(file_name, file_parent, all_data, details, 'all', np.s_[:], args)
    # for stepIdx, stepSlice in enumerate(indicies):
    #     debug(stepIdx, stepSlice)
    #
    #     graph_raw(file_name, file_parent, all_data, details, stepIdx, stepSlice, args)

    if data_json:
        graph_normalized(file_name, file_parent, all_data, details, 'all', np.s_[:], args)
        for stepIdx, stepSlice in enumerate(indicies):
            debug(stepIdx, stepSlice)
            graph_normalized(file_name, file_parent, all_data, details, stepIdx, stepSlice, args)

        totalLength = len(all_data.step.array)
        initialPeriod = 10000
        initialPeriodPlot = 6000
        if len(all_data.step.array) >= initialPeriod:
            graph_normalized(file_name, file_parent, all_data, details, 'initial', np.s_[:initialPeriodPlot], args)
        graph_normalized(file_name, file_parent, all_data, details, 'last', np.s_[totalLength-100:], args)
    else:
        graph_raw(file_name, file_parent, all_data, details, 'all', np.s_[:], args)
        for stepIdx, stepSlice in enumerate(indicies):
            debug(stepIdx, stepSlice)
            graph_raw(file_name, file_parent, all_data, details, stepIdx, stepSlice, args)

        totalLength = len(all_data.step.array)
        initialPeriod = 10000
        initialPeriodPlot = 6000
        if len(all_data.step.array) >= initialPeriod:
            graph_raw(file_name, file_parent, all_data, details, 'initial', np.s_[:initialPeriodPlot], args)
        graph_raw(file_name, file_parent, all_data, details, 'last', np.s_[totalLength-100:], args)
    
            
    
def data_cleanup_uts(data, details):

    if 'load' not in data.keys():
        data.load = data.loadLinearLoad1Maximum # choose Honeywell
        
    if 'displacement' not in data.keys():
        data.displacement = data.displacementLinearDigitalPositionMaximum # choose peak disp

    data.maxes = DataTree()
    data.maxes.displacement = np.argmax(data.displacement.array)
    data.maxes.load = data_find_max('load', data.load.array)
    
    if 'loadLinearLoad1Maximum' in data:
        data.maxes.loadLoad1 = data_find_max('loadLinearLoad1Maximum', data.loadLinearLoad1Maximum.array)
    
    debug(data.maxes)

    if details:
        stress = data.load.array/details.measurements.area.value
        strain = data.displacement.array/details.gauge.length

        # hack    
        data.maxes.stress = data_find_max('stress', stress)
        data.maxes.strain = data_find_max('strain', strain)
    
        # data.stress = PlotData(array=stress, label="Stress", units="MPa", max=None)
        # data.strain = PlotData(array=strain, label="Strain", units="∆", max=None)
        data.stress = PlotData(array=stress, label="Stress|DynaCell", units="MPa", max=None)
        data.strain = PlotData(array=strain, label="Strain|Stretch Ratio", units="λ", max=None)
        
        if 'loadLinearLoad1Maximum' in data:
            stress1 = data.loadLinearLoad1Maximum.array/details.measurements.area.value
            # data.stress1 = PlotData(array=stress1, label="Stress Honeywell", units="MPa", max=None)
            data.stress1 = PlotData(array=stress1, label="Stress|Stress1 Honeywell", units="MPa", max=None)
            data.maxes.stress1 = data_find_max('stress1', stress1)
            data.maxes.loadLoad1 = data_find_max('loadLinearLoad1Maximum', data.loadLinearLoad1Maximum.array)
        
    return (data, details)

def graph_normalized(file_name, file_parent, data, details, stepIdx, npslice, args):
    
    t = makePlotData(data.totalCycles, columnMax=None)
    x = makePlotData(data.strain, columnMax=data.maxes.strain)
    y = makePlotData(data.stress, columnMax=data.maxes.stress)
    
    z = None
    if 'stress1' in data.keys():
        y = makePlotData(data.stress1, columnMax=data.maxes.stress1)
        
    return graph(file_name, file_parent, t, x, y, z, details, stepIdx, npslice, args)

def makePlotData(column, columnMax=None):
    return PlotData(array=column.array, label=column.label, units=column.units, max=columnMax)

def graph_raw(file_name, file_parent, data, details, stepIdx, npslice, args):

    t = makePlotData(data.totalCycles, columnMax=None)
    x = makePlotData(data.displacement, columnMax=data.maxes.displacement)
    y = makePlotData(data.load, columnMax=data.maxes.load)
    
    z = None
        
    return graph(file_name, file_parent, t, x, y, z, details, stepIdx, npslice, args)

def graph(file_name, file_parent, t, x, y, z, details, stepIdx, npslice, args):

    # debug(x.label)
    ax1_title = "trends - (%s vs %s) [step %s]"%(x.label, y.label, stepIdx)
    
    fig, ax1 = plt.subplots(ncols=1, figsize=(14,6))
    ax2 = ax1.twinx() 
    
    # <http://stackoverflow.com/questions/14762181/adding-a-y-axis-label-to-secondary-y-axis-in-matplotlib>
    splitLabel = lambda x: x.label.split('|')

    # First Plot
    # ax1.plot(x.data, y.data)
    # ax1.set_xlabel(x.label)
    # ax1.set_ylabel(y.label)
    #
    # uts_label = "UTS: %4.2f %s, %4.2f %s"%(x.max.value, x.units, x.data[y.max.idx], y.units)
    # ax1.plot(x.data[y.max.idx], y.max.value, 'or', label=uts_label)
    #
    # debug(uts_label)
    #
    # ax1.legend(loc=0, fontsize=10)
    # ax1.set_title(ax1_title)
    
    # Second Plot
    
    ax1.plot(t.array[npslice], x.array[npslice], '-+', color='darkgrey', label=x.label+' [%s]'%x.units)
    ax2.plot(t.array[npslice], y.array[npslice], '--.', label=y.label+' [%s]'%y.units)

    if z:
        ax2.plot(t.array[npslice], z.array[npslice], '--', label=z.label+' [%s]'%z.units)

    ax1.set_xlabel(splitLabel(t)[0]+' $[%s]$'%t.units)
    ax1.set_ylabel(splitLabel(x)[0]+' $[%s]$'%x.units)
    ax2.set_ylabel(splitLabel(y)[0]+' $[%s]$'%y.units)

    if details and 'test_stress' in details.other:
        
        if y.units == 'N':
            factor = details.measurements.area.value
            name = 'F'
        else:
            name = "\\sigma"
            factor = 1.0
            
        test_stress = details.other.test_stress*factor
        uts_stress = details.other.uts_stress*factor
        
        debug(test_stress, uts_stress)
        
        tt = t.array[npslice]
        units = y.units
        
        ax2.plot(tt, [ test_stress for t in tt ], '--', color='orange', label='$%s_{test} [%s]$'%(name, units))
        ax2.plot(tt, [ uts_stress for t in tt ], '--', color='darkred', label='$%s_{uts} [%s]$'%(name, units))

    ax1.legend(loc=2,fontsize=12, fancybox=True, framealpha=0.85)
    ax2.legend(loc=1,fontsize=12, fancybox=True, framealpha=0.85)
    
    # ax2.set_title("Individual Channels for %s"%stepIdx)
    ax2.set_title(("$\\mathbf{Step %s}: \mathsf{Time} \mathit{vs} \mathsf{%s} and \mathsf{%s}$"%
                (stepIdx, splitLabel(x)[-1], splitLabel(y)[-1], )).replace(' ', ' \\  ') )

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

    Graphing.fig_save(fig, os.path.join(file_parent, 'img', 'trends'), name=base_file_name, type='.png', lgd=lgd2)
    # Graphing.fig_save(fig, os.path.join(file_parent, 'img', 'eps'), name=base_file_name, type='.eps', lgd=lgd2)
    
    plt.close()
    
    return



if __name__ == '__main__':

    parser = ScriptRunner.parser
    
    parser.add_argument("-n", "--name", default="data", type=str)
    parser.add_argument("--raw", action='store_true', default=True, help="Run raw ", )  
    parser.add_argument("--normed", action='store_true', default=False,help="Run normalized ", )  

    ## Test
    
    project = "Test4 - transverse fatigue (scilab.mf.pre)/trans-fatigue-trial1/"
    # project = "Test4 - transverse fatigue (scilab.mf.pre)/test4(trans-uts)/"
    
    fileglob = "{R}/{P}/*/*.trends.csv".format(R=RAWDATA,P=project)
    test_args = ["--glob", fileglob] 
    test_args += ['-1'] # only first
    
    args = parser.parse_args( test_args)
    
    # Parse command line if not running test args.
    if 'args' not in locals():
        args = parser.parse_args()
    
    ScriptRunner.process_files_with(args=args, handler=handler)
    
    
    

