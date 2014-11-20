#!/usr/bin/env python3
# coding: utf-8

import csv
import sys, os

from pylab import *
from scipy.stats import exponweib, weibull_max, weibull_min
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator
import glob, logging

from ntm.Tools.Project import *
from ntm.Tools.Graphing import *
from ntm.Tools.InstronCSV import *

from ntm.Tools import Project, Excel, Graphing, ScriptRunner, Json

import ntm.Tools.DataTools as DataTools


PlotData = namedtuple('PlotData', 'array label units max')

def get_max(data):
    idx, value = np.argmax(data)
    return dict(idx=idx, value=value)

def data_find_max(name, data):
    idx = np.argmax(data)
    return DataMax(idx=idx, value=data[idx], name=name)

def handler(file_name, file_object, file_path, file_parent, args):
    
    all_data = csvread(file_path)
    data_json = Json.load_data(file_parent, file_name)    

    debug(all_data.keys())
    
    indicies = all_data._getslices('step')
    
    ramp_start = all_data.totalTime.array[indicies[args.toe_ramp_step]][0]
    
    all_data, details = data_cleanup_uts(all_data, data_json)

    debug(data_json.other)
    
    
    t = all_data.totalTime.array
    dt = (t[-1]-t[0]) / len(t)     
    t0 = int((ramp_start-1.0)/dt) # s
    t1 = int((ramp_start+9.0)/dt)# s
    
    debug(dt, t0, t1, len(t), t[-1])
    
    graph_normalized(file_name, file_parent, all_data, details, 'exp-toe-initial ramp', np.s_[t0:t1], args)
    
def data_cleanup_uts(data, details):

    if 'load' not in data.keys():
        data.load = data.loadLinearLoad # choose Instron

    data.maxes = DataTree()
    data.maxes.displacement = np.argmax(data.displacement.array)
    data.maxes.load = data_find_max('load', data.load.array)
    
    
    debug(data.maxes)
    
    stress = data.load.array/details.measurements.area.value
    strain = data.displacement.array/details.gauge.length

    # hack    
    data.maxes.stress = data_find_max('stress', stress)
    data.maxes.strain = data_find_max('strain', strain)
    
    data.stress = PlotData(array=stress, label="Stress|DynaCell", units="MPa", max=None)
    data.strain = PlotData(array=strain, label="Strain|Stretch Ratio", units="λ", max=None)
        
    if 'loadLinearLoad1' in data:
        stress1 = data.loadLinearLoad1.array/details.measurements.area.value
        data.stress1 = PlotData(array=stress1, label="Stress|Stress1 Honeywell", units="MPa", max=None)
        data.maxes.stress1 = data_find_max('stress1', stress1)
        data.maxes.loadLoad1 = data_find_max('loadLoad1', data.loadLinearLoad1.array)
        
    return (data, details)

def graph_normalized(file_name, file_parent, data, details, stepIdx, npslice, args):
    
    t = makePlotData(data.totalTime, columnMax=None)
    x = makePlotData(data.strain, columnMax=data.maxes.strain)
    y = makePlotData(data.stress, columnMax=data.maxes.stress)
    
    z = None
    if 'stress1' in data.keys():
        y = makePlotData(data.stress1, columnMax=data.maxes.stress1)
        
    return graph(file_name, file_parent, t, x, y, z, details, stepIdx, npslice, args)

def makePlotData(column, columnMax=None):
    longLabel = column.label
    if hasattr(column, 'details'): longLabel += " "+column.details
    return PlotData(array=column.array, label=longLabel, units=column.units, max=columnMax)

def graph_raw(file_name, file_parent, data, details, stepIdx, npslice, args):

    t = makePlotData(data.totalTime, columnMax=None)
    x = makePlotData(data.displacement, columnMax=data.maxes.displacement)
    y = makePlotData(data.load, columnMax=data.maxes.load)
    
    z = None
    if 'loadLinearLoad1' in data.keys():
        y = makePlotData(data.loadLinearLoad1, columnMax=data.maxes.loadLoad1)
        
    return graph(file_name, file_parent, t, x, y, z, details, stepIdx, npslice, args)

def graph(file_name, file_parent, t, x, y, z, details, stepIdx, npslice, args):

    debug(x.label)
    ax1_title = "Details - (%s vs %s) [step %s]"%(x.label, y.label, stepIdx)
    
    fig, ax1 = plt.subplots(ncols=1, figsize=(14,6))
    ax2 = ax1.twinx() # <http://stackoverflow.com/questions/14762181/adding-a-y-axis-label-to-secondary-y-axis-in-matplotlib>

    # First Plot
    
    # Second Plot
    splitLabel = lambda x: x.label.split('|')
    
    # y_ = DataTools.smooth_data(y.array[npslice], window_len=18)
    
    ax1.plot(t.array[npslice], x.array[npslice], '-', color='darkgrey', label=splitLabel(x)[-1]+' $[%s]$'%x.units)
    ax2.plot(t.array[npslice], y.array[npslice], '-+', label=splitLabel(y)[-1]+' $[%s]$'%y.units)
    # ax2.plot(t.array[npslice], y_, '-+', label=splitLabel(y)[-1]+' $[%s]$'%y.units)

    if z:
        ax2.plot(t.array[npslice], z.array[npslice], '-,', label=splitLabel(z)[-1]+' $[%s]$'%z.units)

    ax1.set_xlabel(t.label)
    
    ax1.set_ylabel(splitLabel(x)[0]+' $[%s]$'%x.units)
    ax2.set_ylabel(splitLabel(y)[0]+' $[%s]$'%y.units)
        
    ax1.legend(loc=2,fontsize=12, fancybox=True, framealpha=0.85)
    ax2.legend(loc=1,fontsize=12, fancybox=True, framealpha=0.85)
    ax1.set_title(("$\\mathbf{Step %s}: \mathsf{Time} \mathit{vs} \mathsf{%s} and \mathsf{%s}$"%
                (stepIdx, splitLabel(x)[1], splitLabel(y)[-1], )).replace(' ', ' \\  ') )

    # fig.tight_layout()
    fig.text(.45, .95, file_name)

    t_ = t.array[npslice]
    x_ = x.array[npslice]
    y_ = DataTools.smooth_data(y.array[npslice])

    def _polyfit(ax, deg=2):
        def polyfit(sx, sy):
            fit = np.polyfit(sx, sy, deg=deg)
            ax.plot(sx, np.polyval(fit, sx), color='red')
            print("fit: t[0]=%5.2f fit: %s"%(sx[0], ["%.6f"%f for f in fit ]))
            return fit
        return polyfit

    delta = args.toe_stress_delta
    max_slope = args.toe_stress_max_slope
     
    end_y, _, cond = DataTools.calculate_data_endpoint2(
            t_, y_, delta=1.0, start_at_end=False,
            # max_slope=0.0330, # max_slope=0.045, # for linear
            max_slope=0.02, # max_slope=0.045, # for linear
            # custom=lambda fit: fit[2] > 30,
            polyfit=_polyfit(ax2, deg=1))

    debug(cond)
    
    delta=1.5
    end_x, _, cond = DataTools.calculate_data_endpoint2(
            t_, x_, delta=0.1, start_at_end=False,
            max_slope=0.0029, 
            polyfit=_polyfit(ax1, deg=1))
    debug(cond)

    ff_t0 = t_[end_x]
    ff_t1 = t_[end_y]

    ff_to_t = (ff_t0, ff_t1, (ff_t1-ff_t0) )
    ff_to_x = (x_[end_x], x_[end_y], (x.array[end_y]-x.array[end_x]))
    print(file_name, ", Time to first force, %.2f, %.2f, %s"%ff_to_t, ',', t.units)
    print(file_name, ", Distance to first force, %.2f, %.2f, %s"%ff_to_x, ',', x.units)

    ## 
    from matplotlib.patches import Polygon
    
    ## 
    max_x = max(x.array[npslice])
    verts = [ (t_[end_x], 0), (t_[end_x], max_x), (t_[end_y], max_x), (t_[end_y], 0), ]
    poly = Polygon(verts, alpha=0.1, edgecolor='k')
    ax1.add_patch(poly)
    

    ax1.text(t_[end_x], max_x*0.70, 
        "Toe Region\n\n time:$%.4f %s$\n distance:$%.3e %s$"%(ff_to_t[-1], t.units, ff_to_x[-1], x.units), 
        fontsize=12,bbox={'color':'black', 'alpha':0.2, 'pad':10})
    
    # plt.axhline(y=max(x.array)/2, xmin=end_x[1], xmax = end_y[1], color='orange')    
    # plt.axvline(x=end_x[1], ymin=0, ymax = max(x.array[npslice]), color='darkgreen')
    # plt.axvline(x=end_y[1], ymin=0, ymax = max(y.array[npslice]), color='purple')
    

    region = DataTree()
    region.time_value = ff_to_t[-1]
    region.time_units = t.units
    region.distance_value = ff_to_x[-1] 
    region.distance_units = x.units
    
    data_json = Json.load_data(file_parent, file_name) 
    data_json['calculations'] = {'time-to-first-loading': region}
    Json.update_data(file_parent, file_name, data_json)
        
    
    if args.only_first:
        plt.show(block=True,  )

    def legend_handles(ax, x=0.5, y=-0.1):
        handles, labels = ax.get_legend_handles_labels()
        lgd = ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(x,y))
        return lgd
    
    lgd1 = legend_handles(ax1, x=.1)
    lgd2 = legend_handles(ax2, x=.9)
    
    base_file_name = "%s (%s)"%(file_name[:file_name.index('.steps')], ax1_title)

    Graphing.fig_save(fig, os.path.join(file_parent, 'img', ), name=base_file_name, type='.png', lgd=lgd2)
    # Graphing.fig_save(fig, os.path.join(file_parent, 'img', 'eps'), name=base_file_name, type='.eps', lgd=lgd2)
    
    plt.close()
    
    return



if __name__ == '__main__':

    parser = ScriptRunner.parser
    
    parser.add_argument("-n", "--name", default="data", type=str)
    parser.add_argument("--raw", action='store_true', default=True, help="Run raw ", )  
    parser.add_argument("--normed", action='store_true', default=False,help="Run normalized ", )  

    parser.add_argument("--toe-ramp-step", default=2, type=int)
    parser.add_argument("--toe-stress-delta", default=2, type=float) # not implemented
    parser.add_argument("--toe-stress-max-slope", default=2, type=float) # not implemented

    ## Test
    test_args = []
    
    ## fatigue
    
    # project = "Test4 - transverse fatigue (ntm-mf-pre)/trans-fatigue-trial1/"
    # test_args += ['--toe-begin', '15'] # only first
    # test_args += ['--toe-end', '25'] # only first
    
    ## uts 
    
    project = "Test4 - transverse fatigue (ntm-mf-pre)/test4(trans-uts)/"
    test_args += ['--toe-ramp-step', '3'] 
    
    ## 
    # files
    fileglob = "{R}/{P}/*/*tracking.csv".format(R=RAWDATA,P=project)
    # fileglob = "{R}/{P}/*gf9.2_llm-p1t_l4-x3-run4*/*tracking.csv".format(R=RAWDATA,P=project)
    # fileglob = "{R}/{P}/*09sep17.3-x12-1*/*tracking.csv".format(R=RAWDATA,P=project)
    test_args += ["--glob", fileglob] 
    test_args += ['-1'] # only first
    
    args = parser.parse_args( test_args)
    
    # Parse command line if not running test args.
    if 'args' not in locals():
        args = parser.parse_args()
    
    ScriptRunner.process_files_with(args=args, handler=handler)
    
    
    

