#!/usr/bin/env python3

import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

from scilab.tools.project import *
import numpy as np
import scilab.tools.fitting as Fitting

def process_precondition(matdata, step_idx='idx_2'):

    data = matdata.data
    colinfo = matdata.columninfo
    
    sl = slice( *matdata.indexes["step"][step_idx] )

    cycletime = data.elapsedCycles[sl]+data.cycleElapsedTime[sl]
    
    cycle_num = 20.0
    timerange_cycle = cycle_num+0.5*np.array([2/3, 3/3])

    sl_fit = slice(*cycletime.searchsorted( timerange_cycle ))
    sl_cycle = slice(*cycletime.searchsorted([cycle_num, cycle_num+1]))
    sl_half = slice(*cycletime.searchsorted([cycle_num, cycle_num + 1.0/2.0 ]))

    # Precond Fitting 
    modulus, fits = fit_modulus(time=cycletime, strain=data.strain[sl], stress=data.stress[sl], sl=sl_fit)
    
    debug(modulus)

    calcs = DataTree(modulus=modulus, fits=fits)
    
    return calcs

def fit_modulus(time, strain, stress, sl):
    
    dbg_strain = DataTree()
    dbg_stress = DataTree()
    
    strain_linear = Fitting.LinearFitData.fit_leastsq( time[sl], strain[sl], dbg=dbg_strain)
    stress_linear = Fitting.LinearFitData.fit_leastsq( time[sl], stress[sl], dbg=dbg_stress)
    
    debug(dbg_strain, dbg_stress)
    debug(strain_linear, stress_linear)
    
    linear_modulus = stress_linear.data.slope / strain_linear.data.slope
    
    # =============
    # = Save Data =
    # =============
    
    # save dyn mod
    modulus = DataTree()
    
    modulus.sl = sl.start, sl.stop, sl.step
    
    ## Expr Fits
    modulus['data','tangent_modulus'] = DataTree(value=linear_modulus, units="MPa/∆")
    modulus['data','strain_linear_slope'] = DataTree(units="∆",**strain_linear.data._asdict())
    modulus['data','stress_linear_slope'] = DataTree(units="MPa",**stress_linear.data._asdict())
        
    fits = DataTree()
    fits.strain_linear = strain_linear.data._asdict()
    fits.strain_linear["rsquared"] = strain_linear.rsquared
    fits.stress_linear = stress_linear.data._asdict()
    fits.stress_linear["rsquared"] = stress_linear.rsquared
    
    return modulus, fits
