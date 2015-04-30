#!/usr/bin/env python3
import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

from scilab.tools.project import *
import numpy as np
import scilab.tools.fitting as Fitting

from scilab.datahandling.datahandlers import *
import scipy.ndimage, skimage

def graphimage(test, axes, imageName, measureName, testfolder):

    scale = test.details.measurements[imageName]["parameters"]["scale"]
    zoomfactor = test.details.measurements[imageName]["parameters"]["zoomfactor"]
    middle = test.details.measurements[imageName]["thirds"]["middle"]
    middleValues = test.details.measurements[imageName]["thirds"]["middleValues"]
    boundingbox = test.details.measurements[imageName]["boundingbox"]
    rawboundingbox = test.details.measurements[imageName]["rawboundingbox"]
    middleidxs = test.details.measurements[imageName]["thirds"]["indexes"]["middle"]
    measureValue = test.details.measurements["image"][measureName]
    
    # debug(test.details)
    debug(scale, zoomfactor, middle, measureValue)
    
    processedFolder = testfolder.images / 'processed' 
    imgadjusted  = loadimage( processedFolder / '{}.adjusted.png'.format(imageName) )
    imgbinarized = loadimage( processedFolder / '{}.binarized.png'.format(imageName) )
    imgcropped   = loadimage( processedFolder / '{}.cropped.png'.format(imageName) )
    
    imgbinarized = imgbinarized.astype('bool') # change to bools... otherwise scaling issues (e.g. 255)
    ax_main, ax_adj, ax_bw, ax_width = axes

    ax_main.set_title(imageName)
    
    # Main
    ax_main.imshow(imgcropped)
    # ax_main.contour(imgbinarized, linewidth=0.5, colors='y')

    # Adjusted
    ax_adj.imshow(imgadjusted  )
    ax_adj.contour(imgbinarized, levels=[0], colors='y', alpha=0.8)
    
    # Binary
    ax_bw.imshow(imgbinarized, label="Binarized")
    
    # Width
    height_data = -np.arange(0, imgbinarized.shape[0])/scale.value
    height_data = height_data[::-1]*-1
    width_data = np.sum(imgbinarized, 1)/scale.value
    ax_width.plot(width_data, height_data,  color='purple')
    # ax_width.set_xlim(0, 3 * scale.value/zoomfactor.value)
    # ax_width.set_ylim(-imgbinarized.shape[0]/scale.value, 0)
    ax_width.set_xlabel('Summed Width [mm]')
    ax_width.set_xlabel('Height [mm]')
    
    # Measurebox
    
    ax_width.fill_betweenx( 
        height_data[middleidxs], width_data[middleidxs], 
        color="blue", alpha=0.10);
    
    y0, y1 = ax_width.get_ylim()
    ax_width.annotate("Avg Width:%5.2f"%(measureValue.value), xy=(0.1,0.2))
    ax_width.vlines(measureValue.value, y0, y1, label='Measured Value')
    ax_width.vlines(middle.value, y0, y1, color='green', label='Measure Std.Dev.', linestyles=[(0,(9,3,4,4))])
    ax_width.legend()

    return 
    

def graph(test, matdata, args, zconfig=DataTree(), **graph_args):

    if not (zconfig['stage']=='norm' and 'precond' in zconfig['method'] and zconfig['item']=='tracking'):
        logging.warning("Graph doesn't match graph type: "+repr(zconfig))
        return DataTree()
    

    testinfo = test.info
    testfolder = test.folder
    
    fig, (axr1, axr2) = plt.subplots(ncols=4, nrows=2, figsize=(12,8), )
                                                # gridspec_kw=DataTree(width_ratios=[2,2,2,1]))

    fig.suptitle("Image Measurement", fontsize=18, fontweight='bold') 
    
    graphimage(test, axr1, "frontImage", "width", testfolder)
    graphimage(test, axr2, "sideImage", "depth", testfolder)

    return DataTree(fig=fig, calcs=DataTree())
    
