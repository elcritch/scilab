#!/usr/bin/env python3

import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator

from scilab.tools.project import *
import scilab.tools.scriptrunner as ScriptRunner
from scilab.tools.instroncsv import csvread
import scilab.tools.jsonutils as Json
import scilab.tools.project as Project
import scilab.tools.excel as Excel
import scilab.tools.graphing as Graphing
from scilab.tools.graphing import DataMax
import numpy as np

PlotData = namedtuple('PlotData', 'array label units max')

from scilab.expers.mechanical.fatigue.uts import TestInfo
from scilab.expers.mechanical.fatigue.uts import FileStructure

# from addict import Dict 

def get_max(data):
    idx, value = np.argmax(data)
    return DataTree(idx=idx, value=value)

def data_find_max(data):
    idx = np.argmax(data)
    return DataMax(idx=idx, value=data[idx], name=None)

def graphs2_handler(testinfo, testfolder, args, testdata, **kwargs):
    
    handler(testinfo, testfolder, details=testdata.details, testdata=testdata, args=args, )
    

def handler(testinfo:TestInfo, testfolder:FileStructure, details:DataTree, testdata:DataTree, args:DataTree):
    
    data = testdata.tracking

    debug(details)
    
    data = data_cleanup_uts(testinfo, data, details)
    
    print(" --------- \n")
    debug(data.maxes)
    debug(data.balances)
    
    maxes = DataTree()
    for m,v in data.maxes.items():
        # debug(m,v, type(v.idx))
        maxes[m] = {'idx':int(v.idx), 'value':v.value}
    
    # debug(maxes)
    
    print("Writing: "+args.experJsonCalc.as_posix()+testinfo.name+'.uts.calculated.json')
    Json.write_json(
        args.experJsonCalc.as_posix(), 
        {'calculations': {'maxes':maxes, 'balances': data.balances } },
        json_url=testinfo.name+'.uts.calculated.json', 
        dbg=False )
    
    # graph_uts_raw(testinfo, data, details, args)
    graph_uts_normalized(testinfo, data, details, args)
    

def data_cleanup_uts(testinfo:TestInfo, data, details):
    
    if 'load' not in data.keys():
        if testinfo.orientation == 'tr':
            loads = [ l for l in ['loadLinearMissus','loadLinearLoad1'] if l in data ]
        if testinfo.orientation == 'lg':
            loads = [ l for l in ['loadLinearLoad'] if l in data ]
        
        logging.warn("Choosing loads: "+repr(loads))
        data.load = data[loads[0]]

    def dovalues(val, sl):
        xx = val.array[sl]
        return DataTree(mean=xx.mean(),std=xx.std(),mins=min(xx),maxs=max(xx))

    s0_sl = data._getslices('step')[1]
    
    data.balances = DataTree()
    data.balances.slices = repr(s0_sl)
    data.balances.load =  dovalues(data.load, s0_sl)
    data.balances.displacement =  dovalues(data.displacement, s0_sl)
    
    data.balances.offset = DataTree(load=data.balances.load.mean)
    
    # data.load_orig = data.load
    data.load = PlotData(array=data.load.array - data.balances.load.mean,
                        label=data.load.label, units=data.load.label, max=None)
    
    data.maxes = DataTree()
    data.maxes.displacement = data_find_max(data.displacement.array)
    data.maxes.load = data_find_max(data.load.array)
    data.maxes.load_peak_displacement = DataTree(idx=data.maxes.load.idx, value=data.displacement.array[data.maxes.load.idx])
    
    debug(data.maxes)
    
    stress = data.load.array/details.measurements.area.value
        
    gauge = details.gauge.value
    strain = data.displacement.array/gauge
    
    data.maxes.strain = data_find_max(strain)
    data.maxes.stress = data_find_max(stress)
    data.maxes.stress_peak_strain = DataTree(idx=data.maxes.stress.idx, value=data.displacement.array[data.maxes.stress.idx])
    
    data.stress = PlotData(array=stress, label="Stress", units="MPa", max=None)
    data.strain = PlotData(array=strain, label="Strain", units="∆", max=None)
    
    # [ get_initial_values(name) for name in 'strain stress'.split()]
    
    # if testinfo.orientation == 'tr':
    #     stress1 = data.loadLinearLoad1.array/details.measurements.area.value
    #     data.stress1 = PlotData(array=stress1, label="Stress Honeywell", units="MPa", max=None)
    #     data.maxes.stress1 = data_find_max(stress1)
    #     data.maxes.loadLoad1 = data_find_max(data.loadLinearLoad1.array)
        
    return data

def makePlotData(column, columnMax=None):
    return PlotData(array=column.array, label=column.label, units=column.units, max=columnMax)
    
def graph_uts_normalized(testinfo:TestInfo, data, details, args):
    
    t = makePlotData(data.totalTime, columnMax=None)
    x = makePlotData(data.strain, columnMax=data.maxes.strain)
    y = makePlotData(data.stress, columnMax=data.maxes.stress)
    
    graph_uts(testinfo, t, x, y, details, args, data=data)


# def graph_uts_raw(testinfo:TestInfo, data, details, args):
#
#     t = makePlotData(data.totalTime, columnMax=None)
#     x = makePlotData(data.displacement, columnMax=data.maxes.displacement)
#     y = makePlotData(data.load, columnMax=data.maxes.load)
#
#     return graph_uts(testinfo, t, x, y, details, args)


def graph_uts(testinfo:TestInfo, t, x, y, details, args, data):
    
    ax1_title = "UTS %s vs %s"%(x.label, y.label)
    
    fig, (ax1,ax2) = plt.subplots(ncols=2, figsize=(14,6))    
    # ax2 = ax1.twinx() # <http://stackoverflow.com/questions/14762181/adding-a-y-axis-label-to-secondary-y-axis-in-matplotlib>

    # First Plot
    ax1.plot(x.array, y.array)
    ax1.set_xlabel(x.label)
    ax1.set_ylabel(y.label)
    
    loadbalance = -data.balances.offset.load/details.measurements.area.value
    ax1.hlines(loadbalance, x.array[0],x.array[-1], linestyles='dashed')
        
    uts_label = "UTS: (%.2f, %.2f) [%s,%s]"%(y.max.value, x.array[y.max.idx], y.units, x.units, )
    uts_peak = (x.array[y.max.idx], y.max.value)
    
    limiter = lambda v, d, oa=0.0,ob=0.0: ( (1.0-d)*(min(v)+oa),(1.0+d)*(max(v)+ob) )
    labeler = lambda x: "{label} [{units}]".format(**x.__dict__)
    
    ax1.set(xlim=limiter(x.array, 0.08), ylim=limiter(y.array, 0.08,oa=loadbalance))
    
    ax1.scatter(uts_peak[0], uts_peak[1])
    
    ax1.annotate(uts_label, xy=uts_peak, xytext=(+30, -20), 
                    bbox=dict(boxstyle="round", fc="0.9"),
                    textcoords='offset points', 
                    arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"),
                    )

    debug(uts_label)
    
    ax1.legend(loc=0, fontsize=10)
    ax1.set_title(ax1_title)
    
    # Strain plot
    
    # Second Plot
    ax2.plot(t.array, x.array, label=labeler(x))
    ax2.plot(t.array, y.array, label=labeler(y))
    ax2.set_xlabel(t.label)

    ax2.legend(loc=0,fontsize=10, )
    ax2.set_title("Individual Channels")

    # fig.tight_layout()
    # fig.text(.45, .95, testinfo.name)
    fig.suptitle('UTS Failure: '+str(testinfo))

    if args.only_first:
        plt.show(block=True,  )

    def legend_handles(ax, x=0.5, y=-0.1):
        handles, labels = ax.get_legend_handles_labels()
        lgd = ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(x,y))
        return lgd
    
    # lgd1 = legend_handles(ax1, x=.1)
    lgd1 = None
    lgd2 = legend_handles(ax2, x=.9)
    
    imgname = 'graph_uts - %s.png'%str(testinfo)
    imgpath = args.experReportGraphs.resolve() / imgname 
    
    debug(imgpath)
    
    # Graphing.fig_save(fig, str(imgpath), name='graph_uts - %s'%str(testinfo), type='.png', lgd=lgd2)
    fig.subplots_adjust(hspace=1.4, )
    
    if data:
        # Make some room at the bottom
        fig.subplots_adjust(bottom=0.20, left=0.20, right=0.80, top=0.90)
        
        def set_labels(axes, xx, xp, ax_dir='x',side='bottom', 
                        convertfunc=lambda x: 1.0*x, position=('outward',40)):
            ax1twiny = axes.twiny() if ax_dir=='x' else axes.twinx()
    
            Gax1twiny = lambda s: getattr(ax1twiny, s.format(x=ax_dir))
            Gaxes = lambda s: getattr(axes, s.format(x=ax_dir))
            
            oldaxvalues = np.array(Gaxes('get_{x}ticks')())
            oldbounds = np.array(Gaxes('get_{x}lim')())
            newbounds = convertfunc(oldbounds)
            # ax1Xlabels = np.array(Gax1twiny('get_{x}ticklabels')())
            # ax1Idxs = xx.array.searchsorted(ax1Xs)
            # ticks_cycles = np.linspace(newbounds[0], newbounds[-1], len(ax1Xs))
            ticks_cycles = convertfunc(oldaxvalues)
            # debug(ticks_cycles, oldbounds, newbounds, oldaxvalues)
            # debug(ax_dir, xx.array[::100], ax1Xs, ax1Idxs, ax1Xs.shape, xp.array.shape, ticks_cycles)
    
            Gax1twiny('set_{x}ticks')      ( ticks_cycles )
            Gax1twiny('set_{x}bound')      ( newbounds )
            Gax1twiny('set_{x}ticklabels') ( [ "{:.0f}".format(i) for i in ticks_cycles ], rotation='vertical')
            Gax1twiny('set_{x}label')      ( xp.label+' [%s]'%xp.units)

            Gax1twiny('set_frame_on')(True)
            Gax1twiny('patch').set_visible(False)
            Gax1twiny('{x}axis').set_ticks_position(side)
            Gax1twiny('{x}axis').set_label_position(side)
            Gax1twiny('spines')[side].set_position(position)
        
        set_labels(ax1, xx=data.strain, xp=data.displacement, 
                    convertfunc=lambda x: x*details.gauge.value)
        
        set_labels(ax1, xx=data.stress, xp=data.load, ax_dir='y', side='right',
                    convertfunc=lambda x: x*details.measurements.area.value, position=('outward',0))
        

        # I'm guessing you want them both on the bottom...    
    
    
    fig.savefig(str(imgpath), bbox_inches='tight',)
    # fig.savefig(str(imgpath), bbox_inches='tight', pad_inches=0.2,  )
    
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

    projectspath = Path(RESEARCH) / '07_Experiments'
    projectpath = projectspath/'fatigue failure (UTS, exper1)'
    
    experUtsCsv = projectpath / '04 (uts) uts-test' 
    experUtsPreconds = projectpath / '02 (uts) preconditions' 
    experData = projectpath / 'test-data'/'uts (expr-1)'
    experExcel = experData/'01 Excel' 
    experJson = experData/'00 JSON'
    experReport = experData/'02 Reports'
    experReportGraphs = experData/'03 Graphs'
    experJsonCalc = experJson / 'calculated'
    
    files = experExcel.glob('*.xlsx')
    
    
    test_args = [] 
    # test_args += ["--glob", fileglob]
    # test_args += ['-1'] # only first
    
    args = parser.parse_args( test_args)
    
    # Parse command line if not running test args.
    if 'args' not in locals():
        args = parser.parse_args()
    
    [ setattr(args,e,v) for e,v in locals().items() if e.startswith('exper' )]
    
    
    for testfile in list(files)[:]:
        
        try:            
            debug(testfile)            
            testinfo = TestInfo(name=testfile.stem)
            debug(testinfo)
            
            jsonfile = experJsonCalc / testfile.with_suffix('.calculated.json').name
            jsonfile = jsonfile.resolve()
            
            data_json = Json.load_json(jsonfile.parent, json_url=jsonfile.name)
        
            def findTestCsv(csvTestParent, testfile):
                testfiles = [ t for t in csvTestParent.glob(testfile.stem+'*') if t.is_dir() ]
                if not testfiles:
                    raise Exception("Cannot find matching csv test folder: "+testfile.stem+" "+csvTestParent.as_posix())
                elif len(testfiles) > 1:
                    testfile = sorted(testfiles, key=lambda x: x.stem )[0]
                    logging.warn("Multiple csv test files match, choosing: "+testfile.name)
                    return testfile
                else:
                    return testfiles[0]
                
                        
            trackingtest = findTestCsv(experUtsCsv, testfile)
            trackingtest = next(trackingtest.glob('*.tracking.csv'))
            debug(trackingtest)
            
            handler(trackingtest, testinfo, data_json, args=args)
            
        except Exception as err:
            logging.warn(err)
            raise err
        
    # ScriptRunner.process_files_with(args=args, handler=handler)
    