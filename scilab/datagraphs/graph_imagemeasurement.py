#!/usr/bin/env python3
import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

from scilab.tools.project import *
import numpy as np
import scilab.tools.fitting as Fitting

from scilab.datahandling.datahandlers import *

def graphimage(test, axes, imageName, testfolder):

    scale = test.details.measurements[imageName]["parameters"]["scale"]
    zoomfactor = test.details.measurements[imageName]["parameters"]["zoomfactor"]
    middle = test.details.measurements[imageName]["thirds"]["middle"]
    
    # debug(test.details)
    debug(scale, zoomfactor, middle)
    
    processedFolder = testfolder.images / 'processed' 
    imgadjusted  = loadimage( processedFolder / '{}.adjusted.png'.format(imageName) )
    imgbinarized = loadimage( processedFolder / '{}.binarized.png'.format(imageName) )
    imgcropped   = loadimage( processedFolder / '{}.cropped.png'.format(imageName) )
        
    ax_main, ax_adj, ax_width = axes

    
    # Main
    ax_main.imshow(imgcropped)
    ax_main.contour(imgbinarized, linewidth=0.5, colors='b')

    # Binary
    ax_adj.imshow(imgadjusted  )
    
    # Width
    avg_width = middle.value - middle.stdev
    
    ax_width.plot(np.sum(imgbinarized, 1)/scale.value/zoomfactor.value,-np.arange(0, imgbinarized.shape[0])/scale.value,  color='purple' )
    
    # ax_width.set_xlim(0, 3 * scale.value)
    ax_width.annotate("Avg Width:%5.2f"%(avg_width), xy=(0,0))
    ax_width.vlines(avg_width, 0, -imgbinarized.shape[0]/scale.value)
    ax_width.vlines(middle.value, 0, -imgbinarized.shape[0]/scale.value, color='green')

    return 
    

def graph(test, matdata, args, zconfig=DataTree(), **graph_args):

    if not (zconfig['stage']=='norm' and 'precond' in zconfig['method'] and zconfig['item']=='tracking'):
        logging.warning("Graph doesn't match graph type: "+repr(zconfig))
        return DataTree()
    

    testinfo = test.info
    testfolder = test.folder
    
    fig, (axr1, axr2) = plt.subplots(ncols=3, nrows=2, figsize=(12,8), 
                                                gridspec_kw=DataTree(width_ratios=[2,2,1]))

    fig.suptitle("Image Measurement", fontsize=18, fontweight='bold') 
    
    graphimage(test, axr1, "frontImage", testfolder)
    graphimage(test, axr2, "sideImage", testfolder)

    return DataTree(fig=fig, calcs=DataTree())
    
