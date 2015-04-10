#!/usr/bin/env python3
# coding: utf-8


import scipy.stats as sps
import numpy as np
import matplotlib.pyplot as plt

import os, sys, math
import pylab
from collections import namedtuple
import collections, json

if __name__ != '__main__':
    from scilab.tools.project import *
else:
    from Project import *


def find_index(t, times):
    for i, tau in enumerate(times):
        if t < tau:
            return i


IndexedValue = namedtuple('IndexedValue', 'idx value') 

def data_find_max(value, data):
    idx_max, value_max = find_max_index_value(data[value])

    maxPoint = IndexedValue(idx_max, value_max)    
    data['max_%s_pair'%value] = maxPoint


def calculate_data_endpoint2(
        x, y, 
        start_x   = None,
        delta     = 5.0, # 5.0,
        max_slope = None, # 0.01, 
        max_value = None, # 0.0, 
        min_value = None, # -5.0,
        max_std   = None, # 0.1,
        start_at_end = True,
        custom = lambda fit: False,
        polyfit   = np.polyfit,
        deg = 1):
    """ Find last point where data does not change. 
    The end point of the data is calculated by breaking the data into
    sections and fitting straight lines to each section. The sections
    are traversed in reverse until the first section with a 
    slope, averaged fit value, or std. dev. that exceed the max values is found. 
    """
    if start_x:
        xidx = find_index(start_x, x)
    
    delta_x = len(x)/(find_index(x[0]+delta, x)-find_index(x[0]+0.0, x))
    
    sections_i = np.array_split(list(range(0,len(x)-1)), delta_x)
    sections_x = np.array_split(x, delta_x)
    sections_y = np.array_split(y, delta_x)
    
    prev_i, prev_sx = sections_i[-1], sections_x[-1]
    
    sections = list(zip(sections_i, sections_x, sections_y))
    
    if start_at_end:
        sections = reversed(sections)
        
    for i, sx, sy in sections:
        if start_x and not sx[0] >= start_x:
            continue
        
        # print(deg)
        fit = polyfit(sx, sy, deg)
        # debug(fit)
        slope, intercept = fit[-2:]
        
        # fix for bug of using intercept instead of initial height
        line_values = np.polyval(fit, sx)
        # slope, initial = (line_values[-1]-line_values[0])/2., fit[-1]
        # avg_fit_value = (line_values[0]+line_values[-1.0])/2.0
        avg_fit_value = line_values.std()
        
        # Algorithm
        std = np.std(sy)
        # debug("%.6f"%slope)
#         _debg_print(locals())
        conds = {
            'slope': slope > max_slope if max_slope else False,
            'std': abs(std) > max_std if max_std else False,
            'max_value': avg_fit_value > max_value if max_value else False,
            'min_value': avg_fit_value < min_value if min_value else False,
            'custom': custom(fit),
        }
    
        if any(conds.values()):
            return ( int((i[0]+i[-1])/2), (sx[0]+sx[-1])/2.0, conds)
        else:
            prev_i, prev_sx = i, sx
    return (0, x[0], {'empty_data'})

def _debg_print(v):
         # print abs(v['slope']) > v['max_slope']
         # print v['intercept'] > v['max_value']
         # print v['intercept'] < v['min_value']
         # print abs(v['std']) > v['max_std']
         print([ (n, v[n]) for n in ['slope', 'avg_fit_value', 'std'] ])


#### Test calculate_data_endpoint

# In[11]:

if __name__ == '__main__':
    
    import sympy 


# In[12]:

if __name__ == '__main__':    
    print("Testing")
    
    # Create function
    x = sympy.Symbol('x')
    f = sympy.Piecewise(
        (10*sympy.sin(1/2.*sympy.pi*x)+10.0, x<10), 
        (5.0*sympy.sin(1/2.*sympy.pi*x)*sympy.exp(-(x-10)/2.0)+5, x<30),
        (0.1*sympy.sin(4.*sympy.pi*x), x>=30),
        )
    fx = sympy.lambdify(x, f, "numpy")

    # Plots
    fig, ax = plt.subplots()
    x1 = np.linspace(0, 50, 1000)
    y1 = [ fx(x) for x in x1 ]
    
    ax.plot(x1, y1)
    ax.set_xlabel('time')
    ax.set_ylabel('Y')

    # Debug method
    def _polyfit(sx, sy, deg=1):
        fit = np.polyfit(sx, sy, deg=deg)
        ax.plot(sx, np.poly1d(fit)(sx))
        print("fit: t[0]=%5.2f slope=%8.4f intcpt:%8.4f std:%5.2f"%(                    sx[0], fit[0], fit[1],np.std(sy)))
        return fit

    end_idx, end_t, _ = calculate_data_endpoint(x1, y1, max_value=1.0, polyfit=_polyfit)
    print("end:", end_idx, end_t)
    ax.plot(end_t, y1[end_idx], 'or')

    plt.show(block=True,  )

    
# In[13]:

if __name__ == '__main__':
    
    import sympy 
    print("Testing")
    
    # Create function
    x = sympy.Symbol('x')
    f = sympy.Piecewise(
        (5.0*sympy.sin(1/2.*sympy.pi*x)*sympy.exp(-(x-10)/3.0)+5, x<20),
        (0, x<30.0),
        (10.0*sympy.sin(5*sympy.pi*x), x<35.0),
        (0.1*sympy.sin(4.*sympy.pi*x), x>=0.0),
        )
    fx = sympy.lambdify(x, f, "numpy")

    # Plots
    fig, ax = plt.subplots()
    x1 = np.linspace(0, 50, 1000)
    y1 = [ fx(x) for x in x1 ]
    
    ax.plot(x1, y1)
    ax.set_xlabel('time')
    ax.set_ylabel('Y')

    # Debug method
    def _polyfit(sx, sy, deg=1):
        fit = np.polyfit(sx, sy, deg=deg)
        ax.plot(sx, np.poly1d(fit)(sx))
        print("fit: t[0]=%5.2f slope=%8.4f intcpt:%8.4f std:%5.2f"%            (sx[0], fit[0], fit[1], np.std(sy)))
        return fit

    end_idx, end_t, cond = calculate_data_endpoint(x1, y1, max_value=1.0, max_std=1.0, polyfit=_polyfit)
    print("end:", end_idx, end_t, cond)
    ax.plot(end_t, y1[end_idx], 'or')

    plt.show(block=True,  )


# In[13]:

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
