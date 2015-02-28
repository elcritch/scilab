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
import scilab.tools.jsonutils as Json

from scilab.expers.mechanical.fatigue.uts import TestInfo
from scilab.tools.tables import mdBlock, mdHeader, ImageTable, MarkdownTable

import collections

import scilab.tools.fitting as Fitting

PlotData = collections.namedtuple('PlotData', 'array label units max')
CycleData = collections.namedtuple('CycleData', 'index elapsedCycle time')


def find_index(time, times):
    for i, tau in enumerate(times):
        if time < tau:
            return i


## Main
def data_find_max(name, data):
    idx = np.argmax(data)
    return DataMax(idx=idx, value=data[idx], name=name)


def handler(testinfo, testfolder, data_tracking, details, args):

    print(mdHeader(2, "Test: "+testinfo.name))

    debug(data_tracking.keys())
    
    data = data_cleanup_relaxation(testinfo=testinfo, data=data_tracking, details=details, args=args)
    graph_relaxation(testinfo=testinfo, data=data, details=details, args=args)

    return

def graphs2_handler(testinfo, testfolder, args, testdata, **kwargs):
    
    debug(testdata.tests.preconds.keys())
    
    testdata.details.gaugeLength = testdata.details['gauge']['value']
    testdata.details.area = testdata.details['measurements']['area']['value']
    
    handler(testinfo      = testinfo, 
            testfolder    = testfolder, 
            data_tracking = testdata.tests.preconds.tracking, 
            details       = testdata.details, 
            args          = args)
    

def getElapsedStarts(data, npslice):
    """ get the elapsed cycle times and indicies. """
    elapsedCycles = data.elapsedCycles.array[npslice]
    elapsedIndicies = get_index_slices(elapsedCycles)

    debug(elapsedCycles, elapsedIndicies)

    elapsedCycles = [ CycleData(index=int(e.start),
                                elapsedCycle=int(elapsedCycles[e.start]),
                                time=data.totalTime.array[npslice][e.start])
                        for e in elapsedIndicies.values() ]

    return collections.OrderedDict( (e.elapsedCycle, e) for e in elapsedCycles)


def data_cleanup_relaxation(testinfo:TestInfo, data, details, args):

    debug(data.keys())

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

    # debug(details.area)
    stress = data.load.array/details.measurements.area.value
    strain = data.displacement.array/details.gauge.value

    data.maxes['stress'] = data_find_max('stress', stress)
    data.maxes['strain'] = data_find_max('strain', strain)

    data.stress = PlotData(array=stress, label="Stress", units="MPa", max=None)
    data.strain = PlotData(array=strain, label="Stress", units="∆", max=None)

    debug(data._getslices('step'))
    npslice = data._getslices('step')[args.step]
    debug(args.step, npslice)

    time = data.totalTime.array[npslice]
    debug(time)
    disp = data.displacement()[npslice]
    force = data.load()[npslice]
    stress = data.stress.array[npslice]
    strain = data.strain.array[npslice]


    graph = DataTree()

    ## Expr Data
    graph.time = time
    graph.disp = disp
    graph.force = force
    graph.stress = stress
    graph.strain = strain

    ## Expr Fits
    modulus_fits = fit_modulus_regions(
            testinfo = testinfo,
            details = details,
            args = args,
            data = data,
            time = time,
            disp = disp,
            force = force,
            stress = stress,
            strain = strain,
            npslice = npslice,
            graph = graph,
            )

    graph.modulus_fits = modulus_fits

    return graph

def fit_modulus(region, data, time, disp, force, stress, strain, startCycle, endCycle, elapsedCycles, lastCycles, **kwargs):


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

        t1 = + e1.time + quarterPeriod*(region.start + lag)
        t2 = + e1.time + quarterPeriod*(region.stop + lag)

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
    modulus = DataTree(fits=DataTree())

    modulus.s_ls1 = ls1

    ## Expr Fits
    modulus.fits.strain_linear = strain_linear
    modulus.fits.stress_linear = stress_linear
    modulus.fits.linear_modulus = linear_modulus

    modulus.data_json = {
            'value':linear_modulus,
            'slope_stress':stress_linear.data.slope,
            'slope_strain':strain_linear.data.slope,
            }

    return modulus

def fit_modulus_regions(testinfo, details, args, data, npslice, graph, **kwargs):

    elapsedCycles = getElapsedStarts(data, npslice)

    debug( elapsedCycles )

    startCycle, endCycle = 18, 20

    # Do fits -> Last Three
    ckeys = [ k for k in elapsedCycles.keys() ]
    debug(ckeys)
    cycle_a,cycle_b = elapsedCycles[ckeys[startCycle]], elapsedCycles[ckeys[endCycle]]
    cycle_a,cycle_b = elapsedCycles[ckeys[startCycle]], elapsedCycles[ckeys[endCycle]]
    lastCycles = np.s_[cycle_a.index:cycle_b.index]
    debug(cycle_a, cycle_b, lastCycles)

    _modulus_toe = fit_modulus(
            region=DataTree(start=0.05, stop=0.50),
            data=data,
            startCycle=startCycle,
            endCycle=endCycle,
            elapsedCycles=elapsedCycles,
            lastCycles=lastCycles,
            **kwargs)

    _modulus_lin = fit_modulus(
            region=DataTree(start=0.5, stop=0.95),
            data=data,
            startCycle=startCycle,
            endCycle=endCycle,
            elapsedCycles=elapsedCycles,
            lastCycles=lastCycles,
            **kwargs)

    _modulus_1third = fit_modulus(
            region=DataTree(start=0.05, stop=0.33),
            data=data,
            startCycle=startCycle,
            endCycle=endCycle,
            elapsedCycles=elapsedCycles,
            lastCycles=lastCycles,
            **kwargs)

    _modulus_2thirds = fit_modulus(
            region=DataTree(start=0.33, stop=0.66),
            data=data,
            startCycle=startCycle,
            endCycle=endCycle,
            elapsedCycles=elapsedCycles,
            lastCycles=lastCycles,
            **kwargs)

    _modulus_3third = fit_modulus(
            region=DataTree(start=0.66, stop=0.95),
            data=data,
            startCycle=startCycle,
            endCycle=endCycle,
            elapsedCycles=elapsedCycles,
            lastCycles=lastCycles,
            **kwargs)

    modulus_fits = DataTree()

    ## careful... hacky ##
    ## assign modulii to dict
    for k,v in locals().items():
        if k.startswith('_modulus'):
            modulus_fits[k.lstrip('_modulus_')] = v
            # modulus_fits.straight_modulus = straight_modulus

    graph.s_cycles = lastCycles

    debug(modulus_fits)
    # Json.update_json(testpath=test, data=data_json, dbg=False)
    Json.write_json(
        (args.experJson ).as_posix(),
        DataTree(dynmodfits={ k:v.data_json for k,v in modulus_fits.items() }),
        json_url=testinfo.name+'.preconds.calculated.json',
        dbg=False,
        )

    return modulus_fits

def graph_relaxation(testinfo:TestInfo, data, details, args):

    debug(data.modulus_fits)

    s_cycles = data.s_cycles

    fig, (ax1,ax2) = plt.subplots(2, sharex=True, figsize=(14,8))
    # ax2 = ax1.twinx() # <http://stackoverflow.com/questions/14762181/adding-a-y-axis-label-to-secondary-y-axis-in-matplotlib>
    fig.subplots_adjust(hspace=0.07)

    ax1.plot(data.time[s_cycles], data.strain[s_cycles], label="Stress|DynaCell [MPa]")
    ax1.plot(data.time[s_cycles], data.strain[s_cycles], ) #label="Linear Stress")

    ax2.plot(data.time[s_cycles], data.stress[s_cycles], ) #label="Strain|Stretch Ratio [λ]", )
    ax2.plot(data.time[s_cycles], data.stress[s_cycles], ) #label="Linear Stretch Ratio", )

    for name, modulus in data.modulus_fits.items():
        s_ls1 = modulus.s_ls1
        ax2.plot(data.time[s_ls1], modulus.fits.stress_linear( data.time[s_ls1]), '-',
                    label='{}:{:.2f} R²:{:.1f}'.format(name, modulus.fits.linear_modulus, modulus.fits.stress_linear.rsquared) )

    ax1.set_ylabel('$Stretch Ratio [\lambda]$')
    ax2.set_ylabel('$Stress [MPa]$')


    ax1.set_title("Linear Modulus Strain/Stress Fit (%.1f%% of %.2f mm)"%(modulus.fits.linear_modulus, details.gaugeLength))
    message1 = "Linear Modulus:%5.2f"%modulus.fits.linear_modulus

    handles, labels = ax1.get_legend_handles_labels()
    lgd1 = ax1.legend(handles, labels) #, bbox_to_anchor=(0.4,-1.09))

    #
    fig.text(.45, -.04, '\n'.join([message1])) #, message2, message3]))

    #
    handles, labels = ax2.get_legend_handles_labels()
    lgd2 = ax2.legend(handles, labels ) #, bbox_to_anchor=(0.9,-0.09))

    imgpath = args.experReportGraphs / testinfo.name

    fig.text(.45, .95, testinfo.name)

    if args.only_first:
        plt.show(block=True, )

    imgpath = args.experReportGraphs

    debug(imgpath)

    Graphing.fig_save(fig, str(imgpath), name="Precondition Fitting - "+imgpath.name, type='.png', lgd=lgd1, lgd2=lgd2)
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

        # save_stdout = sys.stdout
        # save_stderr = sys.stderr
        # sys.stdout = tee(save_stdout, report)
        # sys.stderr = tee(save_stderr, report)


        print(mdHeader(1, "Graphing: Preconditions (UTS Test Expr1)"))

        for testfile in list(files)[:]:

            try:
                process_test(testinfo, testfolder, None)
            except Exception as err:
                logging.error(err)
                raise err


        # sys.stdout = save_stdout
        # sys.stderr = save_stderr

    # ScriptRunner.process_files_with(args=args, handler=handler)
"""
        folder.graphs         = test_dir / 'graphs'
        folder.json           = test_dir / 'json'
        folder.jsoncalc       = folder.json / 'calculated'
        folder.images         = test_dir / 'images'

"""



def process_test(testinfo, testfolder, measurements):




    try:
        details = DataTree()

        if not measurements:
            jsonfile = next(testfolder.jsoncalc.glob('*.measurements.json'))
            jsonfile = jsonfile.resolve()

            debug(jsonfile)

            data_json = Json.load_json(jsonfile.parent, json_url=jsonfile.name)

            # json data
            details.gaugeLength = data_json['gauge']['value']
            details.area = data_json['measurements']['area']['value']
        else:
            details.gaugeLength = float(measurements.gauge)
            details.area = float(measurements.area)

    except KeyError as err:
        raise Exception("Skipping test due to missing data: "+str(err))


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
    args.step = 1
    args.begin = 80.3
    args.end = 4.8
    args.experReportGraphs = testfolder.graphs
    args.experJson = testfolder.jsoncalc
    args.only_first = False

    trackingtestFolder = findTestCsv(testfolder.testfs.raws.preconds_csv, testinfo.name)
    trackingtest = next(trackingtestFolder.glob('*.tracking.csv'))
    debug(trackingtest,trackingtestFolder)

    data_tracking = csvread(trackingtest.as_posix())

    return handler(trackingtest, testinfo, data_tracking=data_tracking, details=details, args=args)


if __name__ == '__main__':
    main()

