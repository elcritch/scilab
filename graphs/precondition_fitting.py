#!/usr/bin/env python3

import shutil, re, sys, os, itertools, argparse, json, collections, logging
import glob, logging

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator

from scilab.tools.project import *
from scilab.tools.graphing import DataMax
from scilab.tools.instroncsv import csvread, get_index_slices

import scilab.tools.project as Project
import scilab.tools.excel as Excel
import scilab.tools.graphing as Graphing 
import scilab.tools.scriptrunner as ScriptRunner
import scilab.tools.json as Json

from scilab.expers.mechanical.fatigue.uts import UtsTestInfo
from scilab.tools.tables import mdBlock, mdHeader, ImageTable, MarkdownTable

import collections

import scilab.tools.fitting as Fitting

PlotData = namedtuple('PlotData', 'array label units max')
CycleData = namedtuple('CycleData', 'index elapsedCycle time')


def find_index(time, times):
    for i, tau in enumerate(times):
        if time < tau:
            return i


## Main
def data_find_max(name, data):
    idx = np.argmax(data)
    return DataMax(idx=idx, value=data[idx], name=name)


def handler(trackingtest, testinfo, data_tracking, data_json, args):

    print(mdHeader(2, "Test: "+testinfo.name))

    debug(data_json)
    
    if not data_json:
        raise Exception("relax_stage: Cannot process file: "+file_path)
        
    try:
        # json data
        details = DataTree()
        details.gaugeLength = data_json['gauge']['value']        
        details.area = data_json['measurements']['area']['value']
    except KeyError as err:
        raise Exception("Skipping test due to missing data: "+str(err))
        
    data, details = data_cleanup_relaxation(testinfo, data_tracking, details, data_json, args)    
    graph_relaxation(testinfo=testinfo, data=data, details=details, args=args)

    return


def getElapsedStarts(data, npslice):
    """ get the elapsed cycle times and indicies. """
    elapsedCycles = data.elapsedCycles.array[npslice]
    elapsedIndicies = get_index_slices(elapsedCycles)
    
    debug(elapsedCycles, elapsedIndicies)
    
    elapsedCycles = [ CycleData(index=int(e.start), 
                                elapsedCycle=int(elapsedCycles[e.start]), 
                                time=data.totalTime.array[npslice][e.start]) 
                        for e in elapsedIndicies ]
    
    return collections.OrderedDict( (e.elapsedCycle, e) for e in elapsedCycles)


def data_cleanup_relaxation(testinfo:UtsTestInfo, data, details, data_json, args):
    
    data.maxes = {}
    data.maxes['displacement'] = data_find_max('displacement', data.displacement.array)

    if 'load' not in data.keys():

        if testinfo.orientation == 'tr':
            loads = [ l for l in ['loadLinearMissus','loadLinearLoad1'] if l in data ]
        if testinfo.orientation == 'lg':
            loads = [ l for l in ['loadLinearLoad'] if l in data ]
        
        logging.warn("Choosing loads: "+repr(loads))
        data.load = data[loads[0]]

    # if 'load' not in data.keys():
    #     if 'loadLinearLoad1' in data:
    #         data.load = data.loadLinearLoad1 # choose Instron
    #     elif 'loadLinearLoad' in data:
    #         data.load = data.loadLinearLoad
        
    debug(details.area)
    
    stress = data.load()/details.area
    strain = data.displacement()/details.gaugeLength

    data.maxes['stress'] = data_find_max('stress', stress)
    data.maxes['strain'] = data_find_max('strain', strain)
    
    data.stress = PlotData(array=stress, label="Stress", units="MPa", max=None)
    data.strain = PlotData(array=strain, label="Stress", units="∆", max=None)
    
    npslice = data._getslices('step')[args.step]
    debug(args.step, npslice)
    
    time = data.totalTime.array[npslice]
    debug(time)
    disp = data.displacement()[npslice]
    force = data.load()[npslice]
    stress = data.stress.array[npslice]
    strain = data.strain.array[npslice]
        
    elapsedCycles = getElapsedStarts(data, npslice)        

    debug( elapsedCycles )
    
    startCycle, endCycle = 19, 20
    
    # Do fits -> Last Three
    ckeys = [ k for k in elapsedCycles.keys() ]
    debug(ckeys)
    cycle_a,cycle_b = elapsedCycles[ckeys[startCycle]], elapsedCycles[ckeys[endCycle]]
    cycle_a,cycle_b = elapsedCycles[ckeys[startCycle]], elapsedCycles[ckeys[endCycle]]
    lastCycles = np.s_[cycle_a.index:cycle_b.index]
    debug(cycle_a, cycle_b, lastCycles)

    # ==================
    # = Linear Modulus =
    # ==================
    def find_linear_slice(n, elapsedCycles, time, data):
        
        e1, e2 = elapsedCycles[n], elapsedCycles[n+1]
    
        cyclePeriod = (e2.time-e1.time)
        quarterPeriod = cyclePeriod/2
        # lag = abs(tslice * (sine_fit.phase%sine_fit.freq)/sine_fit.freq )
        lag = 0.0
        
        ## Ugggh, this is ugly, but it's working. :) 
        # time = data.totalTime.array[npslice]
        # lag = 0.08 # seconds # estimate of viscoelastic lag....
        t1 = + e1.time + quarterPeriod*(0.00 + lag)
        t2 = + e1.time + quarterPeriod*(0.50 + lag)
        
        debug(e1, e2, cyclePeriod, lag, quarterPeriod, e1.time, t1, t2, find_index(t2, time))
        print()
        debug(time, t1, t2, find_index(t1, time), find_index(t2, time))
        linearSlice = np.s_[find_index(t1, time) : find_index(t2, time)]
        debug(linearSlice)
        return linearSlice
    
    ls1 = find_linear_slice(startCycle+1, elapsedCycles, time, data)
    
    
    dbg_strain = DebugData()
    dbg_stress = DebugData()
    
    strain_linear = Fitting.LinearFitData.fit_leastsq( time[ls1], strain[ls1], dbg=dbg_strain)
    stress_linear = Fitting.LinearFitData.fit_leastsq( time[ls1], stress[ls1], dbg=dbg_stress)
    
    debug(dbg_strain, dbg_stress)
    debug(strain_linear, stress_linear)
    
    linear_modulus = stress_linear.data.slope / strain_linear.data.slope
    
    # =============
    # = Save Data =
    # =============

    # save dyn mod
    data_json['linear_modulus'] = { 
            'value':linear_modulus, 
            'slope_stress':stress_linear.data.slope, 
            'slope_strain':strain_linear.data.slope, 
            }
    
    debug(data_json['linear_modulus'])
    # Json.update_json(testpath=test, data=data_json, dbg=False)
    Json.write_json(
        (args.experJson / 'calculated').as_posix(), 
        {'linear_modulus': data_json['linear_modulus']}, 
        json_url=testinfo.name+'.preconds.calculated.json', 
        dbg=False,
        )
    
    graph = DataTree()
    
    # graph.time = time
    graph.time = time
    graph.s_ls1 = ls1
    graph.s_cycles = lastCycles
    
    ## Expr Data 
    graph.disp = disp
    graph.force = force
    graph.stress = stress
    graph.strain = strain
    
    ## Expr Fits
    graph.strain_linear = strain_linear
    graph.stress_linear = stress_linear
    graph.linear_modulus = linear_modulus
    
    return (graph, details)

def graph_relaxation(testinfo:UtsTestInfo, data, details, args):
    
    s_cycles = data.s_cycles
    
    fig, (ax1,ax2) = plt.subplots(2, sharex=True, figsize=(14,8))
    # ax2 = ax1.twinx() # <http://stackoverflow.com/questions/14762181/adding-a-y-axis-label-to-secondary-y-axis-in-matplotlib>
    fig.subplots_adjust(hspace=0.07)

    ax1.plot(data.time[s_cycles], data.strain[s_cycles], label="Stress|DynaCell [MPa]")
    ax2.plot(data.time[s_cycles], data.stress[s_cycles], label="Strain|Stretch Ratio [λ]", )

    s_ls1 = data.s_ls1
    ax1.plot(data.time[s_cycles], data.strain[s_cycles], label="Linear Stress")
    ax2.plot(data.time[s_cycles], data.stress[s_cycles], label="Linear Stretch Ratio", )
    ax2.plot(data.time[s_ls1], data.stress_linear( data.time[s_ls1]), '-', 
                label='Linear Modulus {:.2f}'.format(data.stress_linear.rsquared) )

    ax1.set_ylabel('$Stretch Ratio [\lambda]$')
    ax2.set_ylabel('$Stress [MPa]$')


    ax1.set_title("Linear Modulus Strain/Stress Fit (%.1f%% of %.2f mm)"%(data.linear_modulus, details.gaugeLength))
    message1 = "Linear Modulus:%5.2f"%data.linear_modulus

    handles, labels = ax1.get_legend_handles_labels()
    lgd1 = ax1.legend(handles, labels) #, bbox_to_anchor=(0.4,-1.09))
    #
    fig.text(.45, -.04, '\n'.join([message1])) #, message2, message3]))
    
    #
    handles, labels = ax2.get_legend_handles_labels()
    lgd2 = ax2.legend(handles, labels ) #, bbox_to_anchor=(0.9,-0.09))

    base_file_name = "%s (%s)"%(testinfo.name, "modulus")
    imgpath = args.experReportGraphs / testinfo.name 
    
    fig.text(.45, .95, testinfo.name)
    
    if args.only_first:
        plt.show(block=True, )
        
    imgpath = args.experReportGraphs / str(testinfo)
    
    debug(imgpath)
    
    Graphing.fig_save(fig, str(imgpath), name=imgpath.name, type='.png', lgd=lgd1, lgd2=lgd2)    
    # Graphing.fig_save(fig, os.path.join(file_parent, 'img', 'eps'), name=base_file_name, type='.eps', lgd=lgd, lgd2=lgd2)
    
    plt.close()
    
    return
    

def main():
    """  """
    parser = ScriptRunner.parser
    
    parser.add_argument("-n", "--name", default="data", type=str)
    parser.add_argument("-s", "--step", default=0, type=int)
    parser.add_argument("-b", "--begin", default=75, type=float)
    parser.add_argument("-e", "--end", default=10, type=float)

    test_args = []
    
    ## Test
    projectspath = Path(RESEARCH) / '07_Experiments'
    projectpath = projectspath/'fatigue failure (UTS, exper1)'
    
    # files = []
    # files += projectpath.glob('02*/nov*/*.tracking.csv')
    
    experUtsCsv = projectpath / '04 (uts) uts-test' 
    experUtsPreconds = projectpath / '02 (uts) preconditions' 
    experData = projectpath / 'test-data'/'uts (expr-1)'
    experExcel = experData/'01 Excel' 
    experJson = experData/'00 JSON'
    experReport = experData/'02 Reports'
    experReportGraphs = experData/'03 Graphs'
    experJsonCalc = experJson / 'calculated'
    
    files = experExcel.glob('*.xlsx')
    
    
    # project = "Test4 - transverse fatigue (ntm-mf-pre)/trans-fatigue-trial1/"
    test_args += ['--step', '1'] # only first

    # project = "Test4 - transverse fatigue (ntm-mf-pre)/test4(trans-uts)/"
    # test_args += ['--step', '1'] # only first
    
    test_args += ['--begin', '80.30'] # only first
    test_args += ['--end', '4.8'] # only first
    
    # fileglob = "{R}/{P}/*/*.tracking.csv".format(R="/Users/elcritch/GDrive/Research/",P=project)
    # fileglob = "{R}/{P}/*/*.tracking.csv".format(R=RAWDATA,P=project)
    # fileglob = "{R}/{P}/*/09sep16.1-x3-4.steps.tracking.csv".format(R=RAWDATA,P=project)
    
    # test_args += ["--glob", fileglob]
    # test_args += ['-1'] # only first
    
    args = parser.parse_args( test_args)
    
    [ setattr(args,e,v) for e,v in locals().items() if e.startswith('exper' )]
    
    
    with (args.experReport/'Temp Reports'/'Graph - Log - Preconditioning Results.md').open('w') as report:
        
        class tee:
            def __init__(self, _fd1, _fd2) :
                self.fd1 = _fd1
                self.fd2 = _fd2

            def __del__(self) :
                if self.fd1: 
                    if self.fd1 != sys.stdout and self.fd1 != sys.stderr :
                        self.fd1.close()
                
                if self.fd2 != sys.stdout and self.fd2 != sys.stderr :
                    self.fd2.close()

            def write(self, text) :
                if self.fd1: self.fd1.write(text)
                self.fd2.write(text)

            def flush(self) :
                if self.fd1: self.fd1.flush()
                self.fd2.flush()

        save_stdout = sys.stdout
        save_stderr = sys.stderr
        sys.stdout = tee(save_stdout, report)
        sys.stderr = tee(save_stderr, report)

        
        print(mdHeader(1, "Graphing: Preconditions (UTS Test Expr1)"))
        
        for testfile in list(files)[:]:
        
            try:
                debug(testfile.name, file=sys.stderr)
                testinfo = UtsTestInfo(name=testfile.stem)
                debug(testinfo)
            
                jsonfile = experJson / 'calculated' / testfile.with_suffix('.calculated.json').name
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
                
                        
                trackingtest = findTestCsv(experUtsPreconds, testfile)
                trackingtest = next(trackingtest.glob('*.tracking.csv'))
                debug(trackingtest)
            
                data_tracking = csvread(trackingtest.as_posix())
            
                handler(trackingtest, testinfo, data_tracking=data_tracking, data_json=data_json, args=args)

            except Exception as err:
                logging.error(err)
                # raise err


        sys.stdout = save_stdout
        sys.stderr = save_stderr
        
    # ScriptRunner.process_files_with(args=args, handler=handler)
    
    
if __name__ == '__main__':
    main()


