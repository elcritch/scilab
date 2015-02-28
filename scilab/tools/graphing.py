import csv, json
import sys, os

from scipy.stats import exponweib, weibull_max, weibull_min

import matplotlib.pyplot as plt

from pylab import *
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator
import glob, logging

sys.path.append(".")
from scilab.tools.project import *

# from DataToolsPy3 import *
# from WaveMatrixToolsPy3 import find_max_index_value
# from WaveMatrixToolsPy3 import *
# import DefaultGraphsPy3

import distutils.dir_util
import collections, pathlib

def fig_save(fig, FigureDir, name, lgd=None, lgd2=None, type=".png", dbg=None):

    if dbg: debug(FigureDir)

    figname = pathlib.Path(str(FigureDir)) / (name+type)

    if dbg: print("Saving figure:", figname)

    distutils.dir_util.mkpath(FigureDir)

    bbox_extra_artists = [ l for l in [lgd, lgd2] if l]

    # fig.tight_layout()
    fig.subplots_adjust(hspace=1.2, )

    fig.savefig(str(figname), bbox_inches='tight', pad_inches=0.2, bbox_extra_artists=bbox_extra_artists,  )

    # fig.savefig(FigureDir+name+".png", bbox_inches='tight', pad_inches=0.2  )
    # fig.savefig('samplefigure', bbox_extra_artists=(lgd,), bbox_inches='tight')

    return (figname)


def reduce_data(test, x_name, y_name):
    end_idx, end_t, end_cond = DataTools.calculate_data_endpoint(
            test[x_name], test[y_name], delta=1.0, max_slope=0.5, max_value=4.0)

    res = {}
    for k,v in test.items():
        if type(v) is np.ndarray:
            res[k] = v[0:end_idx]
        else:
            res[k] = v

    return (res, (end_idx, end_t, end_cond))


DataMax = collections.namedtuple('DataMax', 'idx value name')

def get_data_find_max(name, data):
    arr = data[name].array
    idx = arr.argmax()
    value_max = DataMax(idx=idx, value=arr[idx], name=name)
    return value_max

def get_max(data):
    idx, value = np.argmax(data)
    return DataTree(idx=idx, value=value)

def data_find_max(data):
    idx = np.argmax(data)
    return DataMax(idx=idx, value=data[idx], name=None)
