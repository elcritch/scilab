#!/usr/bin/env python3
import sys, os, glob, logging
from collections import namedtuple
from pathlib import Path

import matplotlib.pyplot as plt

from scilab.tools.project import *
import numpy as np
import scilab.tools.fitting as Fitting


import scilab.expers.mechanical.fatigue.run_image_measure as run_image_measure

def processimg(gamma, gain, ricis_factor, img_otsu, sobel_otsu,
               remove_small, remove_small_pre, 
               min_size, auto_otsu, equalize_adapthist, dofindedge,
               img, scale, title=""):
        image = np.copy(img[:,:,0])
    
        fig, ((ax1,ax2), (ax3, ax4)) = plt.subplots(ncols=2, nrows=2, figsize=(14,10), 
                                                    gridspec_kw=DataTree(width_ratios=[1,1], height_ratios=[3,1]))

    
        ax_main, ax_hist, ax_bw, ax_width = ax1, ax3, ax2, ax4

        fig.suptitle(title, fontsize=18, fontweight='bold') 
        
        image = ski.exposure.adjust_gamma(image, gamma=gamma, gain=gain)
    
        if equalize_adapthist:
            image = ski.exposure.equalize_adapthist  (image ) 
    
        ax_main.imshow(img)
        if auto_otsu:
            img_otsu = ski.filter.threshold_otsu(image)
        img_bw = (image > img_otsu)
    
        if remove_small_pre:
            img_bw = morphology.remove_small_objects(img_bw, min_size=min_size, connectivity=2)


        img_bw_lens = lambda aa: aa.shape[1] - np.argmax( aa[:, ::-1] > 0, 1 ) - np.argmax( aa > 0, 1)
        img_valid_widths = np.array(img_bw_lens(img_bw) < 200,dtype='int')* np.array(np.sum(img_bw,1) < 2*scale,dtype='int') 
        img_bw = np.array([ r*s for r, s in zip(img_bw, img_valid_widths) ], dtype=img_bw.dtype)

        if remove_small:
            img_bw = morphology.remove_small_objects(img_bw, min_size=min_size, connectivity=2)

        ax_bw.imshow( img_bw )
        ax_bw.annotate("Otsu:%5.2f"%img_otsu, xy=(0,0))

        if dofindedge:
    #         img_edge = findedge(img_bw, sobel_otsu)
            ax_main.contour(img_bw, [0.2], lw=1, colors='r')
    
        # Display histogram
        imagef = image
        counts, centers = ski.exposure.histogram(imagef, nbins=128) 
        ax_hist.plot(centers[1::], counts[1::])

        ax_width.plot(np.sum(img_bw, 1),-np.arange(0, img_bw.shape[0]),  color='purple' )
        ax_width.set_xlim(0, 3 * scale)
        avg_width = np.mean(np.sum(img_bw[200:250], 1)) - np.std(np.sum(img_bw[200:250], 1))
        ax_width.annotate("Avg Width:%5.2f"%(avg_width/scale), xy=(0,0))
        ax_width.vlines(avg_width, 0, -img_bw.shape[0])
        ax_width.vlines(avg_width + np.std(np.sum(img_bw[200:250], 1)), 0, -img_bw.shape[0], color='green')

        plt.tight_layout()
        return 
    

def graph(test, matdata, args, zconfig=DataTree(), **graph_args):

    if not (zconfig['stage']=='norm' and 'precond' in zconfig['method'] and zconfig['item']=='tracking'):
        logging.warning("Graph doesn't match graph type: "+repr(zconfig))
        return DataTree()
    
    import scilab.expers.mechanical.fatigue.run_image_measure as run_image_measure

    testinfo = test.info
    testfolder = test.folder
    
    try:
        if (test.folder.jsoncalcs/"{}.measurements.calculated.json".format(test.info.short)).exists():
                return DataTree()
        measurements = run_image_measure.process_test(testinfo, testfolder)
        debug(measurements)
        
    except Exception as err:
        logging.error(err)
        return DataTree()
    
    
    return DataTree()
    
