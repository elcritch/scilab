#!/usr/bin/env python3

import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

sys.path.insert(0,[ str(p) for p in Path('.').resolve().parents if (p/'scilab').exists() ][0] )

from scilab.tools.project import *
import scilab.tools.scriptrunner as ScriptRunner
from scilab.tools.instroncsv import csvread
import scilab.tools.jsonutils as Json
import scilab.tools.project as Project
import scilab.tools.excel as Excel
import scilab.tools.graphing as Graphing
from scilab.tools.graphing import DataMax
import numpy as np

from scilab.graphs.graph_shared import *

def normalize_data(testinfo:TestInfo, testdetails, testdata, testargs):
    
    

def handler(testinfo:TestInfo, testfolder:FileStructure, details:DataTree, testdata:DataTree, args:DataTree):
    
    testname = 'cycles'
    csvdata = testdata.tests[testname].tracking
    
    data = data_configure_load(testinfo=testinfo, data=csvdata, details=details, 
                               balancestep='step_2', data_kind='tracking')
    
    data.total_time = csvdata.totalTime
    # data.summaries = DataTree()
    
    # debug(displayjson(data))
    
    updated = lambda d1,d2: [ d1.summaries[k].update(v) for k,v in d2.items() ]
    
    data.update( data_normalize(testinfo, data, details) )
    
    ## Save Summaries ##
    testfolder.save_calculated_json(name='summaries', data={'step04_cycles':data.summaries})
    
    ## Figure ##
    fig, ax = graph(testinfo=testinfo, testdata=data, testdetails=details, testargs=args)    
    # plt.show(block=True)
    testfolder.save_graph(name='graph_all_'+testname, fig=fig)
    plt.close()
    
    
    return {}

def graphs2_handler(testinfo, testfolder, testdata, args, **kwargs):
    
    return handler(testinfo, testfolder, details=testdata.details, testdata=testdata, args=args, )    

    
if __name__ == '__main__':
    
    import scilab.graphs.graph_runner2
    scilab.graphs.graph_runner2.main()

