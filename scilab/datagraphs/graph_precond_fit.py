#!/usr/bin/env python3

import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

from scilab.tools.project import *
import numpy as np
import scilab.tools.fitting as Fitting

def graph(test, matdata, args, step_idx='idx_2', zconfig=DataTree(), **graph_args):

    data = matdata.data
    colinfo = matdata.columninfo
    
    debug(zconfig)
    
    if not ( zconfig['stage'] == 'norm' and 'precond' in zconfig['method'] and zconfig['item'] == 'tracking' ):
        logging.warning("Graph doesn't match graph type: "+repr(zconfig))
        return DataTree()
    
    labeler = lambda x: "{label} [{units}]".format(label=x.label, units=x.units)
    
    sl = slice( *matdata.indexes.step.idx_2 )

    cycletime = data.elapsedCycles[sl]+data.cycleElapsedTime[sl]
    
    cycle_num = 20.0
    timerange_cycle = cycle_num+0.5*np.array([2/3, 3/3])

    sl_fit = slice(*cycletime.searchsorted( timerange_cycle ))
    sl_cycle = slice(*cycletime.searchsorted([cycle_num, cycle_num+1]))
    sl_half = slice(*cycletime.searchsorted([cycle_num, cycle_num + 1.0/2.0 ]))

    fig, (ax1,ax2) = plt.subplots(ncols=1,nrows=2)

    ax1.plot(
        cycletime[sl_cycle], 
        data.stress [sl][sl_cycle],
        label=colinfo.stress.name)
    
    ax1.set_xlabel(labeler(colinfo.cycleElapsedTime))
    ax1.set_ylabel(labeler(colinfo.stress))

    ax2.plot(
        data.strain [sl][sl_half],
        data.stress [sl][sl_half],
        label=colinfo.strain.name)

    ax2.set_xlabel(labeler(colinfo.strain))
    ax2.set_ylabel(labeler(colinfo.stress))

    fig.subplots_adjust(hspace=0.5, )

    # Precond Fitting 
    modulus, fits = fit_modulus(time=cycletime, strain=data.strain[sl], stress=data.stress[sl], sl=sl_fit)
    
    debug(modulus)
    
    ax1.plot(cycletime[sl_fit], fits.stress_linear( cycletime[sl_fit]),
            '--', label='{}: R²:{:.2f}'.format("Fit", fits.stress_linear.rsquared),
            lw=4.0,
            color='black',
            )

    textpoint = (timerange_cycle[1] - timerange_cycle[0])/2+ timerange_cycle[0]
    ax1.annotate('Tangent Modulus: {:.2f}'.format(modulus.data.linear_modulus, ),
                 xy=(textpoint,fits.stress_linear(textpoint)),
                 xytext=(-10, 10),
                 va='top',
                 xycoords="data",
                 textcoords='offset points',
                 horizontalalignment='right',
                 fontsize=12,
                    bbox=dict(boxstyle="round", fc="0.9"),
                # arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"),
                )
    

    # fig.suptitle("(test=902-6LG-402 | stage=norm | item=tracking | method=precond | v0")
    fig.suptitle("Precond: {} ({})".format(test.info.short, repr(zconfig))
)

    ax1.legend()
    ax2.legend()

    return DataTree(fig=fig, axes=(ax1,ax2), calcs=DataTree(modulus=modulus))

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
    
    modulus['data','linear_modulus'] = linear_modulus
    modulus['data','strain_linear'] = strain_linear.data._asdict()
    modulus['data','stress_linear'] = stress_linear.data._asdict()
    
    modulus.data_json = {
            'value':linear_modulus,
            'slope_stress':stress_linear.data.slope,
            'slope_strain':strain_linear.data.slope,
            }
    
    fits = DataTree()
    fits.strain_linear = strain_linear
    fits.stress_linear = stress_linear
    
    return modulus, fits
