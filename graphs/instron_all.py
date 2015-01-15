#!/usr/bin/env python3
# coding: utf-8

import csv
import sys, os

from pylab import *
from scipy.stats import exponweib, weibull_max, weibull_min
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator
import glob, logging

base = "/Users/jaremycreechley/cloud/bsu/02_Lab/01_Projects/01_Active/Meniscus (Failure Project)/07_Experiments/fatigue failure (cycles, expr1)/05_Code/01_Libraries"
sys.path.insert(0,base)

from scilab.tools.project import *
from scilab.tools.graphing import *
from scilab.tools.instroncsv import *

import scilab.tools.project as Project
import scilab.tools.excel as Excel
import scilab.tools.graphing as Graphing
import scilab.tools.scriptrunner as ScriptRunner
import scilab.tools.json as Json

from scilab.tools.tables import mdBlock, mdHeader, ImageTable, MarkdownTable

from scilab.expers.mechanical.fatigue.cycles import FileStructure
from scilab.expers.mechanical.fatigue.cycles import TestInfo as TestInfo
from scilab.expers.mechanical.fatigue.helpers import *
import scilab.tools.json as Json

from scilab.expers.mechanical.fatigue.cycles import TestInfo

PlotData = namedtuple('PlotData', 'array label units max')




def get_max(data):
    idx, value = np.argmax(data)
    return dict(idx=idx, value=value)

def data_find_max(name, data):
    idx = np.argmax(data)
    return DataMax(idx=idx, value=data[idx], name=name)

def handler(trackingtest, testinfo, data_tracking, details, args):
    
    print("## Test: "+testinfo.name,"\n")
    debug(trackingtest)
    
    all_data = data_tracking
    # all_data = csvread(file_path)
    # data_json = Json.load_data(file_parent, file_name)
    data_json = None

    debug(all_data.keys())
    
    indicies = all_data._getslices('step')
    
    all_data, details = data_cleanup_uts(testinfo, all_data, data_json)

    # steps    
    graph_raw(testinfo,  all_data, details, 'all', np.s_[:], args)

    # debug(data_json.other)
    
    # if True:
        # return

    for stepIdx, stepSlice in enumerate(indicies):
        debug(stepIdx, stepSlice)

        graph_raw(testinfo,  all_data, details, stepIdx, stepSlice, args)

    if data_json:
        graph_normalized(testinfo,  all_data, details, 'all', np.s_[:], args)
        for stepIdx, stepSlice in enumerate(indicies):
            debug(stepIdx, stepSlice)
            graph_normalized(testinfo,  all_data, details, stepIdx, stepSlice, args)

    totalLength = len(all_data.totalTime.array)
    initialPeriod = 10000
    initialPeriodPlot = 6000
        
    # if totalLength >= initialPeriod:
    graph_raw(testinfo,  all_data, details, 'initial', np.s_[:initialPeriodPlot], args)
    graph_raw(testinfo,  all_data, details, 'last', np.s_[totalLength-5000:], args)
        
        
    if data_json:
        if totalLength >= initialPeriod:
            graph_normalized(testinfo,  all_data, details, 'initial', np.s_[:initialPeriodPlot], args)
        graph_normalized(testinfo,  all_data, details, 'last', np.s_[totalLength-5000:], args)
    
def data_cleanup_uts(testinfo, data, details):

    # if 'load' not in data.keys():
    #     data.load = data.loadLinearLoad # choose Instron

    if 'load' not in data.keys():

        if testinfo.orientation == 'tr':
            loads = [ l for l in ['loadLinearMissus','loadLinearLoad1'] if l in data ]
        if testinfo.orientation == 'lg':
            loads = [ l for l in ['loadLinearLoad'] if l in data ]

        logging.warn("Choosing loads: "+repr(loads))
        data.load = data[loads[0]]

    data.maxes = DataTree()
    data.maxes.displacement = np.argmax(data.displacement.array)
    data.maxes.load = data_find_max('load', data.load.array)    
    
    # if 'loadLinearLoad1' in data:
        # data.maxes.loadLoad1 = data_find_max('loadLoad1', data.loadLinearLoad1.array)
    
    debug(data.maxes)
    
    if details:
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
        
    return (data, details)

def graph_normalized(testinfo,  data, details, stepIdx, npslice, args):
    
    t = makePlotData(data.totalTime, columnMax=None)
    x = makePlotData(data.strain, columnMax=data.maxes.strain)
    y = makePlotData(data.stress, columnMax=data.maxes.stress)
    
    z = None
    if 'stress1' in data.keys():
        y = makePlotData(data.stress1, columnMax=data.maxes.stress1)
        
    return graph(testinfo,  t, x, y, z, details, stepIdx, npslice, args)

def makePlotData(column, columnMax=None):
    longLabel = column.label
    if hasattr(column, 'details'): longLabel += " "+column.details
    return PlotData(array=column.array, label=longLabel, units=column.units, max=columnMax)

def graph_raw(testinfo,  data, details, stepIdx, npslice, args):

    t = makePlotData(data.totalTime, columnMax=None)
    x = makePlotData(data.displacement, columnMax=data.maxes.displacement)
    y = makePlotData(data.load, columnMax=data.maxes.load)
    
    z = None
    # if 'loadLinearLoad1' in data.keys():
    #     y = makePlotData(data.loadLinearLoad1, columnMax=data.maxes.loadLoad1)
        
    return graph(testinfo, t, x, y, z, details, stepIdx, npslice, args)

def graph(testinfo, t, x, y, z, details, stepIdx, npslice, args):

    debug(x.label)
    ax1_title = "Overview - (%s vs %s) [step %s]"%(x.label, y.label, stepIdx)
    
    fig, ax1 = plt.subplots(ncols=1, figsize=(14,6))
    ax2 = ax1.twinx() # <http://stackoverflow.com/questions/14762181/adding-a-y-axis-label-to-secondary-y-axis-in-matplotlib>

    # First Plot
    
    # Second Plot
    splitLabel = lambda x: x.label.split('|')
    
    ax1.plot(t.array[npslice], x.array[npslice], '-', color='darkgrey', label=splitLabel(x)[-1]+' $[%s]$'%x.units)
    ax2.plot(t.array[npslice], y.array[npslice], '-+', label=splitLabel(y)[-1]+' $[%s]$'%y.units)

    if z:
        ax2.plot(t.array[npslice], z.array[npslice], '-,', label=splitLabel(z)[-1]+' $[%s]$'%z.units)

    ax1.set_xlabel(t.label)
    
    ax1.set_ylabel(splitLabel(x)[0]+' $[%s]$'%x.units)
    ax2.set_ylabel(splitLabel(y)[0]+' $[%s]$'%y.units)

    if stepIdx == 'last' and z:
        ax2.set_ylim(.85*min(z.array[npslice]), 1.15*max(z.array[npslice]),  )
        
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
    ax1.set_title(("$\\mathbf{Step %s}: \mathsf{Time} \mathit{vs} \mathsf{%s} and \mathsf{%s}$"%
                (stepIdx, splitLabel(x)[1], splitLabel(y)[-1], )).replace(' ', ' \\  ') )

    # fig.tight_layout()
    fig.text(.45, .95, str(testinfo))

    if args.only_first:
        plt.show(block=True,  )

    def legend_handles(ax, x=0.5, y=-0.1):
        handles, labels = ax.get_legend_handles_labels()
        lgd = ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(x,y))
        return lgd
    
    lgd1 = legend_handles(ax1, x=.1)
    lgd2 = legend_handles(ax2, x=.9)
    
    # base_file_name = "%s (%s)"%(file_name[:file_name.index('.steps')], ax1_title)

    imgpath = args.experReportGraphs

    debug(imgpath)

    Graphing.fig_save(fig, str(imgpath), name="%s (%s)"%(ax1_title, testinfo.short()), type='.png', lgd=lgd1, lgd2=lgd2)
    # Graphing.fig_save(fig, os.path.join(file_parent, 'img', 'overview'), name=base_file_name, type='.png', lgd=lgd2)
    # # Graphing.fig_save(fig, os.path.join(file_parent, 'img', 'eps'), name=base_file_name, type='.eps', lgd=lgd2)
    
    plt.close()
    
    return

def process_test(testinfo, testfolder):


    debug(testinfo, testinfo)

    def findTestCsv(csvTestParent, testfile):
        debug(csvTestParent, testfile)

        testfiles = [ t for t in csvTestParent.glob(testfile+'*') if t.is_dir() ]
        if not testfiles:
            raise Exception("Cannot find matching csv test folder: "+testfile+" "+csvTestParent.as_posix())
        elif len(testfiles) > 1:
            testfile = sorted(testfiles, key=lambda x: x.stem )[0]
            logging.warn("Multiple csv test files match, choosing: "+str(testfile) )
            return testfile
        else:
            return testfiles[0]


    # project = "Test4 - transverse fatigue (ntm-mf-pre)/trans-fatigue-trial1/"
#    test_args += ['--step', '1'] # only first

    # project = "Test4 - transverse fatigue (ntm-mf-pre)/test4(trans-uts)/"
    # test_args += ['--step', '1'] # only first

#    test_args += ['--begin', '80.30'] # only first
#    test_args += ['--end', '4.8'] # only first

    args = DataTree()
    args.experReportGraphs = testfolder.graphs
    args.experJson = testfolder.jsoncalc
    args.only_first = False

    data_folder = testfolder.testfs.raws.cycles_lg_csv if testinfo.orientation == 'lg' else testfolder.testfs.raws.cycles_tr_csv

    trackingtestFolder = findTestCsv(data_folder, testinfo.name)
    trackingtest = next(trackingtestFolder.glob('*.tracking.csv'))
    debug(trackingtest,trackingtestFolder)

    data_tracking = csvread(trackingtest.as_posix())

    return handler(trackingtest, testinfo, data_tracking=data_tracking, details=None, args=args)


def main():
    
    
    fs = FileStructure('fatigue failure (cycles, expr1)', 'cycles-expr2')
    # Test test images for now
    test_dir = fs.test_parent.resolve()
    
    
    testitemsd = fs.testitemsd()

    for testinfo, testfile  in testitemsd.items():
        
        # debug(type(testinfo), testinfo, testfile)
        
        try:
            ti = TestInfo(name=testfile.name)
        except:
            ti = None
        
        if not ti:
            continue
        
        testfolder = fs.testfolder(testinfo=ti, ensure_folders_exists=False)

        process_test(ti, testfolder)
    

if __name__ == '__main__':

    main()


if __name__ == '__main__':
    main()


    

