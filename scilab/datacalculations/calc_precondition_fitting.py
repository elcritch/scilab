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

from scilab.datahandling.datahandlers import *
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


def calc(test, matdata, args, zconfig:DataTree):

    step_idx = args.get('step_idx', 'idx_1')
    
    npslice = getattr(matdata.indexes.step, step_idx)
    
    debug(npslice)
    
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

    # debug(modulus_fits)
    # # Json.update_json(testpath=test, data=data_json, dbg=False)
    # Json.write_json(
    #     (args.experJson ).as_posix(),
    #     DataTree(dynmodfits={ k:v.data_json for k,v in modulus_fits.items() }),
    #     json_url=testinfo.name+'.preconds.calculated.json',
    #     dbg=False,
    #     )

    return modulus_fits


def main():
    """docstring for main"""
    
    import scilab.expers.configuration as config
    import scilab.expers.mechanical.fatigue.uts as exper_uts
    parentdir = Path(os.path.expanduser("~/proj/expers/")) / "fatigue-failure|uts|expr1"
    
    pdp = parentdir / 'projdesc.json'     
    fs = config.FileStructure(projdescpath=pdp,testinfo=exper_uts.TestInfo, verify=True)
    
    args = DataTree(version="0")
    
    testname = exper_uts.TestInfo('dec20(gf10.8-llm)-wa-tr-l5-x2')
    folder = fs.testfolder(testinfo=testname)
    
    test = DataTree()
    test.folder = folder
    test.info = testname
    test.details = Json.load_json_from(test.folder.details)
    
    datacombs = datacombinations(test, args, stages = ["norm"],methods = ["precond"], items = ["tracking"])
    debug(datacombs, datacombs.norm.precond.tracking)
    
    
    matdata = load_columns_matlab(datacombs.norm.precond.tracking)
    print(matdata)
    
    
    zconfig = DataTree()
    
    calc(test, matdata, args, zconfig)
    
    


if __name__ == '__main__':
    main()


