import csv, json
import sys, os

from scipy.stats import exponweib, weibull_max, weibull_min

import matplotlib.pyplot as plt

from pylab import *
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator
import glob, logging

sys.path.append(".")
from ntm.Tools.Project import *

# from DataToolsPy3 import *
# from WaveMatrixToolsPy3 import find_max_index_value
# from WaveMatrixToolsPy3 import *
# import DefaultGraphsPy3

import distutils.dir_util 
import collections

def fig_save(fig, FigureDir, name, lgd=None, lgd2=None, type=".png"):
    
    debug(FigureDir)
    
    figname = os.sep.join([FigureDir,name+type])
    print("Saving figure:", figname)
    
    distutils.dir_util.mkpath(FigureDir)

    bbox_extra_artists = [ l for l in [lgd, lgd2] if l]
    
    # fig.tight_layout()
    fig.subplots_adjust(hspace=1.2, )
    
    fig.savefig(figname, bbox_inches='tight', pad_inches=0.2, bbox_extra_artists=bbox_extra_artists,  )
    
    # fig.savefig(FigureDir+name+".png", bbox_inches='tight', pad_inches=0.2  )
    # fig.savefig('samplefigure', bbox_extra_artists=(lgd,), bbox_inches='tight')


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


def get_step_data_as_dict(test_data, stepColumn=ColStep):
    
    steps = test_data.groupby([stepColumn], sort=False)
    
    step_tuples = [ (s,d) for s,d in steps ]
    step_data = OrderedDict( step_tuples )
    
    return step_data
    
DataMax = collections.namedtuple('DataMax', 'idx value name')

def get_data_find_max(name, data):
    idx, value = find_max_index_value(data[name].array)
    value_max = DataMax(idx=idx, value=value, name=name)
    return value_max

def data_find_max(name, data):
    idx, value = find_max_index_value(data[name])
    value_max = DataMax(idx=idx, value=value, name=name)
    data.__setattr__('max_%s_pair'%name, value_max)


def convert_wavematrix_to_data_x(data, **kwargs):
    res = {}
    for k,v in kwargs.items():
        if v in data.columns: 
            res[k] = data.as_matrix([v]).ravel()
        # else:
            # res[k] = None
    
    return res


def get_columns(**kwargs):
    return dict(kwargs)
