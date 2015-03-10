#!/usr/bin/env python3

import os, sys, pathlib, re, collections
import pandas as pd
import numpy as np
import scipy.io as sio
from pandas import ExcelWriter

# sys.path.insert(0,[ str(p) for p in pathlib.Path('.').resolve().parents if (p/'scilab').exists() ][0] )


from scilab.tools.project import *
from scilab.expers.configuration import *
from scilab.tools.instroncsv import *
import scilab.tools.jsonutils as Json

import numpy as np


@unwrap_array
def getmax(array):
    if not len(array):
        return DataTree(idx=None, value=None)
    idx = np.argmax(array)
    return DataTree(idx=idx, value=array[idx])

@unwrap_array
def getmin(array):
    if not len(array):
        return DataTree(idx=None, value=None)
    idx = np.argmin(array)
    return DataTree(idx=idx, value=array[idx])

@unwrap_array
def summaryvalues(array, sl):
    array = array[sl]
    return InstronColumnSummary(mean=array[sl].mean(),std=array[sl].std(),mins=getmin(array[sl]),maxs=getmax(array[sl]))

@unwrap_array
def getslices(data, keyer=lambda x: str(x), k=1, includeall=True, astuple=False):
    """ Return an array of numpy slices for indexing arrays according to changes in the numpy array `data` """
    indices = (np.where(data[:-1] != data[1:])[0]).astype(int)
    indices_begin = [0] + [ i for i in (indices + 1)] # offset by 1 to get beginning of slices
    indices_end = [ i for i in (indices + 1)]+[-1]
    keyer = keyer or (lambda k: k)
    slicer = lambda i,j,k: np.s_[i:j:k] 
    if astuple:
        slicer = lambda i,j,k: {"start":i,"stop":j,"step":k}
    
    slices = collections.OrderedDict( (keyer(data[i]), slicer(i,j,k)) for i,j in zip(indices_begin, indices_end) )
    if includeall:
        slices[keyer(-1)] = slicer(indices_begin[0],indices_end[-1],k)
    
    return slices

def summarize(column, slice_column):
    slices = get_index_slices(slice_column, keyer=lambda x: str(x), includeall=True)
    return DataTree({ sk: summaryvalues(column, sl)
                        for sk, sl in slices.items() } )



def dobalances(colname, summary):
    return InstronColumnBalance(step=balancestep, offset=summary[balancestep].mean)


