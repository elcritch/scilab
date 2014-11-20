#!/usr/bin/env python3

import csv
import sys, os

from pylab import *
from scipy.stats import exponweib, weibull_max, weibull_min
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator
import glob, logging

from ntm.Tools.Project import *
# from ntm.Tools.Graphing import *

import ntm.Tools.Project as Project
import ntm.Tools.Excel as Excel
import ntm.Tools.Graphing as Graphing 
import ntm.Tools.ScriptRunner as ScriptRunner
import ntm.Tools.Json as Json
from ntm.Tools.InstronCSV import csvread
from pprint import pprint

import pandas as pd

def calculate_gauge(file_name, file_object, file_path, file_parent, args):

    # load json
    test_data = csvread(file_path)    
    data_json = Json.load_data(file_parent, file_name)

    debug(data_json)
    
    # update gauge length
    gauge = DataTree()
    gauge.update(data_json.gauge)
    
    debug(test_data.position.array)
    debug(gauge)
    
    gauge.initial = test_data.position.array[0]
    gauge.length = gauge.initial - gauge.init_position 
    
    Json.update_data(file_parent, file_name, {'gauge': gauge}, dbg=True )
    
    return    


def handler(file_name, file_object, file_path, file_parent, args):
    
    calculate_gauge(file_name, file_object, file_path, file_parent, args)

    return 

if __name__ == '__main__':

    parser = ScriptRunner.parser
    
    parser.add_argument("-n", "--name", default="data", type=str)
    parser.add_argument("--raw", action='store_true', default=True, help="Run raw ", )  
    parser.add_argument("--normed", action='store_true', default=False,help="Run normalized ", )  

    ## Test
    # project = "Test4 - transverse fatigue (ntm-mf-pre)/test4(trans-uts)"
    project = "Test4 - transverse fatigue (ntm-mf-pre)/trans-fatigue-trial1/"
    
    fileglob = "{R}/{P}/*/*tracking.csv".format(R=RAWDATA,P=project)
    test_args = ["--glob", fileglob] 
    # test_args += ['-1'] # only first
    
    args = parser.parse_args( test_args)
    
    # Parse command line if not running test args.
    if 'args' not in locals():
        args = parser.parse_args()
    
    ScriptRunner.process_files_with(args=args, handler=handler)
    
    
    

