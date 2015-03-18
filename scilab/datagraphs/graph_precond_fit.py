#!/usr/bin/env python3

import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

from scilab.tools.project import *
import numpy as np
import scilab.tools.fitting as Fitting

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
    modulus = DataTree(fits=DataTree())
    
    modulus.sl = sl.start, sl.stop, sl.step
    
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

def graph(test, matdata, args, step_idx='idx_1', zconfig=DataTree(), **graph_args):

    data = matdata.data
    colinfo = matdata.columninfo
    
    debug(zconfig)
    
    if not (zconfig == DataTree(stage='norm', method='precond', item='tracking')):
        print("Not the graph!!")
        return DataTree()
    else:
        print("GRAPH!!")
    
    debug(matdata.indexes.step._fieldnames)
    sl = slice( *matdata.indexes.step.idx_2 )
    
    # sl = slice(*getattr(matdata.indexes.step, 'idx_1'))

    cycletime = data.elapsedCycles[sl]+data.cycleElapsedTime[sl]
    cycletime_3final = cycletime.searchsorted([18,19,20])

    debug(sl, cycletime, cycletime_3final, )
    
    cycle_num = 20.0
    timerange_cycle = cycle_num+0.5*np.array([2/3, 3/3])

    sl_fit = slice(*cycletime.searchsorted( timerange_cycle ))
    sl_cycle = slice(*cycletime.searchsorted([cycle_num, cycle_num+1]))

    # debughere()
    
    fig, (ax1,ax2) = plt.subplots(ncols=1,nrows=2)

    ax1.plot(
        cycletime[sl_cycle], 
        data.stress [sl][sl_cycle],
        label=colinfo.stress.name)

    ax2.plot(
        cycletime[sl_cycle], 
        data.strain [sl][sl_cycle],
        label=colinfo.strain.name)

    return DataTree(fig=fig, axes=(ax1,ax2), calcs=DataTree())

    # # Fit Stuff
    #
    # modulus = fit_modulus(time=cycletime, strain=data.strain[sl], stress=data.stress[sl], sl=sl_fit)
    #
    # ax1.plot(cycletime[sl_fit], modulus.fits.stress_linear( cycletime[sl_fit]),
    #         '--', label='{}: R²:{:.1f}'.format("Fit", modulus.fits.stress_linear.rsquared),
    #         lw=4.0,
    #         color='black',
    #         )
    #
    # textpoint = (timerange_cycle[1] - timerange_cycle[0])/2+ timerange_cycle[0]
    # ax1.annotate('Tangent Modulus: {:.2f}'.format(modulus.fits.linear_modulus, ),
    # #              xy=(0.05, 0.95),
    # #              arrowprops=dict(facecolor='black', shrink=0.05),
    #              xy=(textpoint,modulus.fits.stress_linear(textpoint)),
    #              xytext=(-10, 10),
    #              va='top',
    # #              xycoords='axes fraction',
    #              xycoords="data",
    #              textcoords='offset points',
    #              horizontalalignment='right',
    #
    #             )
    #
    # fig.suptitle("(test=902-6LG-402 | stage=norm | item=tracking | method=precond | v0")
    #
    # ax1.legend()
    # ax2.legend()
