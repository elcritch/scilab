#!/usr/bin/env python3
# coding: utf-8

import os, sys, functools, itertools, collections, re, logging
from pathlib import *
from tabulate import *

# import matplotlib; matplotlib.use('Qt5Agg')

import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display
import numpy as np, scipy

import scilab, scilab.tools.graphing, scilab.tools.json 
from scilab.tools.project import *
from scilab.expers.mechanical.fatigue.uts import *
from scilab.tools.tables import mdBlock, mdHeader, ImageTable, MarkdownTable
from functools import partial 



def plotAllImages(image_dict, vert=False):
    ncols, nrows =  (1, len(image_dict)) if vert else (len(image_dict), 1)
    fig, axes = plt.subplots(ncols=ncols, nrows=nrows, figsize=(18,14))
    for (name, image), ax in zip(image_dict, axes):
        ax.imshow(image)
        ax.set_title(name)


def legend_handles(ax, x=0.5, y=-0.1):
    handles, labels = ax.get_legend_handles_labels()
    lgd = ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(x,y))
    return lgd

def plotMeasurements(title, img, imgPath, croppedImg, measures):
    debug("plotMeasurements",type(img))
    sns.set_style("whitegrid")
    fig, (ax1, ax2, ax3) = plt.subplots(ncols=3,figsize=(12,6))

    fig.suptitle(title, fontsize=14, fontweight='bold')
    
    x = measures.mm.x
    widths = measures.mm.widths
    ws = measures.mm.summaries.widths
    
    ax1.set_title("Specimen Pixel Width")
    ax1.plot(x, measures.mm.widths)
    
    msgAverage = "Avg {:5.2f} ± ({:5.2f}) [mm]".format(ws.average.mean, ws.average.std)
    ax1.hlines(ws.average.mean, x[0],x[-1], label=msgAverage)

    ax1.fill_between(x[ws.indexes.idx[0]:ws.indexes.idx[1]],
         ws.average.mean-ws.average.std, ws.average.mean+ws.average.std, 
         color="green", alpha=0.10);

#     ax1.hlines(t, [0], s, lw=2)
    ax1.hlines(ws.maxs.value, *ws.indexes.value, label="Max {:5.2f}".format(ws.maxs.value))
    ax1.hlines(ws.mins.value, *ws.indexes.value, label="Min {:5.2f}".format(ws.mins.value))    
    
    lgd1 = legend_handles(ax1, x=.1)

    ax1.set_xlabel("Height (mm)")
    ax1.set_ylabel("Width (mm)")

    ax2.imshow(img)
    ax2.plot()
    ax2.set_title("Specimen Cleaned Image")
    ax2.set_xlabel("Height (Pixels)")
    ax2.set_ylabel("Width (Pixels)")
    px = measures.px
    ax2.hlines(img.shape[0]-measures.px.start.value,0,img.shape[1],color='r',lw=1.0, label="Start")
    ax2.hlines(img.shape[0]-measures.px.stop.value,0,img.shape[1],color='g',lw=1.0, label="Stop")
    ax2.legend(fancybox=True, )
    
    ax3.imshow(croppedImg)
    ax3.set_title("Specimen Cropped Image")
    ax3.set_xlabel("Height (Pixels)")
    ax3.set_ylabel("Width (Pixels)")
    
    
#     plt.tight_layout()

    figname = scilab.tools.graphing.fig_save(
        fig, imgPath.parent.as_posix(), 
        name=imgPath.name, type='.png',
        lgd=lgd1)

    plt.close()
    
    return figname


# # Function: Process
