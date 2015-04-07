#!/usr/bin/env python3
import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

from scilab.tools.project import *
import numpy as np
import scilab.tools.fitting as Fitting


import scilab.expers.mechanical.fatigue.run_image_measure as run_image_measure

def graph(test, matdata, args, zconfig=DataTree(), **graph_args):

    if not (zconfig['stage']=='norm' and 'precond' in zconfig['method'] and zconfig['item']=='tracking'):
        logging.warning("Graph doesn't match graph type: "+repr(zconfig))
        return DataTree()
    
    import scilab.expers.mechanical.fatigue.run_image_measure as run_image_measure

    testinfo = test.info
    testfolder = test.folder
    
    try:
        measurements = run_image_measure.process_test(testinfo, testfolder)
        debug(measurements)
        
    except Exception as err:
        logging.error(err)
        return DataTree()
    
    
    return DataTree()
    
