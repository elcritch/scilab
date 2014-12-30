#!/usr/bin/env python3
# coding: utf-8

import numpy as np
import scipy.signal
from numpy import pi as pi
from scipy.optimize import leastsq
import pylab as plt
import collections
from functools import reduce

from scilab.tools.project import *

# ==================
# = Helper Methods =
# ==================

def smooth_data(data, window='flat', window_len = 9):
    """ Apply smoothing to the data using either a flat window, or other window. 
    
    See http://wiki.scipy.org/Cookbook/SignalSmooth
    """
    
    s=np.r_[data[window_len-1:0:-1],data,data[-1:-window_len:-1]]

    if window == 'flat': #moving average
        w=np.ones(window_len,'d')
    else:
        w=getattr(np, window)(window_len)

    ret = np.convolve(w/w.sum(),s,mode='valid')
    
    return ret[:len(data)] 

def fit_estimate_period_peaks(t, y_data, width_min=10, width_max=20, dbg=None):
    # smooth the data 
    peak_widths = np.array( list(reversed([1.0*len(y_data)/n for n in range(width_min,width_max)]))) 
    
    peakfind = scipy.signal.find_peaks_cwt(y_data, peak_widths )
    t_maxs = np.array([ t[p] for p in peakfind ])
    d_maxs = np.array([ y_data[p] for p in peakfind ])

    peakfind = scipy.signal.find_peaks_cwt(y_data.mean()-y_data, peak_widths )
    t_mins = np.array([ t[p] for p in peakfind ])
    d_mins = np.array([ y_data[p] for p in peakfind ])
    
    if dbg: dbg.y_data = y_data
        
    return ( (t_maxs, d_maxs), (t_mins, d_mins) )

def fit_estimate_period_peaks2(t, y_data, width_min=10, width_max=20, dbg=None):
    # smooth the data 
    y_data = smooth_data(y_data, window_len=20)
    
    
    peak_widths = np.array( list(reversed([1.0*len(y_data)/n for n in range(width_min,width_max)]))) 
    
    peakfind = scipy.signal.argrelmax(y_data, order=50)[0]
    t_maxs = np.array([ t[p] for p in peakfind ])
    d_maxs = np.array([ y_data[p] for p in peakfind ])

    peakfind = scipy.signal.argrelmin(y_data, order=50)[0]       
    t_mins = np.array([ t[p] for p in peakfind ])
    d_mins = np.array([ y_data[p] for p in peakfind ])
    
    if dbg:
        dbg.y_data = y_data
        
    return ( (t_maxs, d_maxs), (t_mins, d_mins))


def fit_sinusoidal_freq_est(t, y_data, dbg=None, peaks_func=fit_estimate_period_peaks2):
    """ Estimate the parameters of the input wave.  """
    (t_maxs, d_maxs), (t_mins, d_mins) = peaks_func(t, y_data)
    
    guess_period_max = np.array(t_maxs[1:]-t_maxs[:-1]).mean()
    guess_period_min = np.array(t_mins[1:]-t_mins[:-1]).mean()
    
    guess_period = (guess_period_max+guess_period_min)/2.0    
    guess_freq = 1.0/(guess_period)
    
#     guess_phase = pi*guess_freq*t[data_zeros[0]] 
    guess_phase = 0.0
    
    if dbg: [ dbg.__setitem__(k,v) for k,v in locals().items() if k not in 't y_data' ]
    
    return (guess_freq, guess_phase)


# ===========
# = FitData =
# ===========

class FitData(object):
    
    @classmethod 
    def leastsq_rsquared(cls, infodict, data, dbg=None):
        """ Perform a fitting using a least squares optimiaztion. """
        ss_err=(infodict['fvec']**2).sum()
        ss_tot=((data-data.mean())**2).sum()
        rsquared=1-(ss_err/ss_tot)
        return rsquared
        
    @classmethod 
    def fit_leastsq(cls, t, data, user_estimate=None, dbg=None):
        """ Perform a fitting using a least squares optimiaztion. """
        guess = cls.estimate(t, data) if not user_estimate else user_estimate
        if dbg: dbg.estimate = guess
        optimized_params, other = leastsq(guess.as_optimize_func(t, data), guess.as_tuple())

        optimized_params,cov,infodict,mesg,ier = leastsq(
            guess.as_optimize_func(t, data), guess.as_tuple(),
            full_output=True, )

        rsquared = cls.leastsq_rsquared(infodict, data, dbg=dbg)
        if dbg: dbg.optimized_params = optimized_params
        # if dbg: dbg.optimized_other = (cov,infodict,mesg,ier, rsquared)
        if dbg: dbg.optimized_other = {'cov': cov,'infodict': infodict,'mesg': mesg,'ier':ier}
        
        fit_lstsq = cls(*optimized_params.tolist(), rsquared=rsquared)
        return fit_lstsq

        # def __new__(cls, left, right):
        #         self = super(Edge, cls).__new__(cls, left, right)


# ===============
# = SineFitData =
# ===============

class SineFitData(FitData):
    
    def __init__(self, amp=0.0, freq=0.0, phase=0.0, mean=0.0, rsquared=None):
        self.Data = namedtuple('Data','amp, freq, phase, mean'.split(', '), rename=True)
        self.data = self.Data(amp, freq, phase, mean)
        self.func = lambda fit, x: fit[0]*np.sin( 2*np.pi*fit[1]*x + fit[2] ) + fit[3]
        self.rsquared = rsquared
        
    def __call__(self, t):
        return self.func(self.as_tuple(), t)

    def as_optimize_func(self, x, y_data):
        optimize_func = lambda fit: self.func(fit, x) - y_data
        return optimize_func
    
    def as_tuple(self):
        return self.data
    
    @classmethod 
    def fit_leastsq(cls, t, data, user_estimate=None, dbg=None):
        fit = super().fit_leastsq(t, data, user_estimate, dbg)
        f = fit.data
        if f[0] < 0.0:
            return cls(*( [abs(f[0]), f[1], f[2]+np.pi, f[3], ]))
        else:
            return fit
        
    @classmethod
    def estimate(cls, t, data, dbg=DebugNone()):
        guess_mean = np.mean(data)
        guess_std = 3*np.std(data)/(2**0.5)
        
        if dbg: dbg.freq_est = DebugData()
            
        # guess_freq, guess_phase = fit_sinusoidal_freq_est(t, data, dbg=dbg.freq_est)
        guess_freq, guess_phase = fit_sinusoidal_freq_est(t, data)
        guess_phase = guess_phase * 2.0*np.pi

        if dbg: [ dbg.__setitem__(k,v) for k,v in locals().items() if k.startswith('guess') ]
        
        return cls(mean=guess_mean, amp=guess_std, phase=guess_phase, freq=guess_freq)
    
    

# =================
# = LinearFitData =
# =================

class LinearFitData(FitData):
    
    def __init__(self, slope=0.0, intercept=0.0, rsquared=None):
        self.Data = namedtuple('Data','slope, intercept'.split(', '), rename=True)
        self.data = self.Data(slope=slope, intercept=intercept)
        self.func = lambda fit, x: fit[0]*x + fit[1]
        self.rsquared = rsquared
        
    def __call__(self, t):
        return self.func(self.as_tuple(), t)

    def as_optimize_func(self, x, y_data):
        optimize_func = lambda fit: self.func(fit, x) - y_data
        return optimize_func
    
    def as_tuple(self):
        return self.data
    
    @classmethod 
    def fit_leastsq(cls, t, data, user_estimate=None, dbg=None):
        fit = super().fit_leastsq(t, data, user_estimate, dbg)
        return fit
        
    @classmethod
    def estimate(cls, t, data, dbg=DebugNone()):
        guess_slope = (max(data)-min(data))/(t[-1]-t[0])
        guess_intercept = t[0]
        
        if dbg: [ dbg.__setitem__(k,v) for k,v in locals().items() if k.startswith('guess') ]
        
        return cls(slope=guess_slope, intercept=guess_intercept)

def find_index(t, times):
    for i, tau in enumerate(times):
        if t < tau:
            return i


# ===========================
# = SineFitWithViscoElastic =
# ===========================

class SineFitWithViscoElastic(FitData):
    
    def __init__(self, decayAmt=0.0, decayRate=0.0, amp=0.0, freq=0.0, phase=0.0, mean=0.0, rsquared=None):
        self.Data = namedtuple('Data','decayAmt, decayRate, amp, freq, phase, mean'.split(', '), rename=True)
        self.data = self.Data(decayAmt, decayRate, amp, freq, phase, mean)
        self.func = lambda fit, x: (fit[0]*np.exp(-fit[1]*x))+fit[2]*np.sin( 2*np.pi*fit[3]*x + fit[4] ) + fit[5]
        self.rsquared = rsquared
        
    def __call__(self, t):
        return self.func(self.as_tuple(), t)

    def as_optimize_func(self, x, y_data):
        optimize_func = lambda fit: self.func(fit, x) - y_data
        return optimize_func
    
    def as_tuple(self):
        return self.data
    
    @classmethod
    def estimate(cls, t, data, dbg=DebugNone()):

        guess_sine = SineFitData.fit_leastsq(t, data).data
        
        guess_initamp = guess_sine.amp/6.0
        guess_halflife = 1/guess_sine.freq

        if dbg: [ dbg.__setitem__(k,v) for k,v in locals().items() if k.startswith('guess') ]        
        
        return cls(mean=guess_sine.mean, amp=guess_sine.amp, phase=guess_sine.phase, freq=guess_sine.freq,
                   decayAmt=guess_initamp, decayRate=guess_halflife)
    


class SineAndExpFitData(FitData):
    
    def __init__(self, decayAmt=0.0, decayRate=0.0, amp=0.0, freq=0.0, phase=0.0, mean=0.0, rsquared=None):
        self.Data = namedtuple('Data','decayAmt, decayRate, amp, freq, phase, mean'.split(', '), rename=True)
        self.data = self.Data(decayAmt, decayRate, amp, freq, phase, mean)
        self.func = lambda fit, x: (fit[0]*np.exp(-fit[1]*x)+fit[2])*np.sin( 2*np.pi*fit[3]*x + fit[4] ) + fit[5]
        self.rsquared = rsquared
        
    def __call__(self, t):
        return self.func(self.as_tuple(), t)

    def as_optimize_func(self, x, y_data):
        optimize_func = lambda fit: self.func(fit, x) - y_data
        return optimize_func
    
    def as_tuple(self):
        return self.data
    
    @classmethod
    def estimate(cls, t, data, dbg=DebugNone()):

        guess_sine = SineFitData.fit_leastsq(t, data).data
        
        guess_initamp = guess_sine.amp/6.0
        guess_halflife = 1/guess_sine.freq

        if dbg: [ dbg.__setitem__(k,v) for k,v in locals().items() if k.startswith('guess') ]        
        
        return cls(mean=guess_sine.mean, amp=guess_sine.amp, phase=guess_sine.phase, freq=guess_sine.freq,
                   decayAmt=guess_initamp, decayRate=guess_halflife)
    

def calculate_dynamic_modulus(stress, strain):
    dyn_modulus = stress.data.amp/strain.data.amp
    dyn_phase =  strain.data.phase - stress.data.phase
    return (dyn_modulus, dyn_phase)

def fit_data_calculate_dynamic_modulus(t, *, stress, strain, dbg=DebugNone()):

    strain_fit = SineFitWithViscoElastic.fit_leastsq(t, strain)
    stress_fit = SineFitWithViscoElastic.fit_leastsq(t, stress)

    dbg.strain, dbg.stress = strain_fit, stress_fit
    
    dyn_modulus, dyn_phase = calculate_dynamic_modulus(stress_fit, strain_fit)
    
    return (dyn_modulus, dyn_phase)

