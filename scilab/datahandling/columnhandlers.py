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

def summarize(column, slice_column):
    slices = get_index_slices(slice_column, keyer=lambda x: str(x), includeall=True)
    return DataTree({ sk: summaryvalues(column, sl)
                        for sk, sl in slices.items() } )



def dobalances(colname, summary):
    return InstronColumnBalance(step=balancestep, offset=summary[balancestep].mean)


