#!/usr/bin/env python3
# coding: utf-8

import matplotlib; 
matplotlib.use('Qt4Agg')

import os, sys, functools, itertools, collections, re, logging
from pathlib import *
from tabulate import *


# import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display
import numpy as np, scipy

import scilab, scilab.tools.graphing, scilab.tools.json 
from scilab.tools.project import *
from scilab.expers.mechanical.fatigue.uts import *
from scilab.tools.tables import mdBlock, mdHeader, ImageTable, MarkdownTable
from functools import partial 
import PIL.Image




import scipy, scipy.ndimage as ndimage
import skimage as ski, skimage.io as io, skimage.feature as feature, skimage.morphology as morphology
import scipy.ndimage as ndimage
from skimage.data import data_dir; from skimage.util import img_as_ubyte; from skimage import io
from IPython.display import *

from image_measurements_plot import *
from helpers import *

TestSet = collections.namedtuple('TestSet', 'front, side, fail')



def runVerification():

    CALIBRATION_DIR = PARENT_DIR/'05 Specimen Images'/'01 Calibration Images'/'verification' 

    verif = DataTree()
    verif.files = DataTree(**{
        'front':'cropped-DSC00600.png',
        'front21':'cropped-DSC00601.png',
        'front22':'cropped-DSC00602.png',
        'front23':'cropped-DSC00603.png',
        'side':'cropped-DSC00598.png',
        'front_eraser':'cropped-DSC00594.png',
        'front_eraser_rot':'cropped-DSC00594 2.png',
        'side_eraser':'cropped-DSC00596.png',
        })

    verif.files = {k: (CALIBRATION_DIR/n).resolve() for k,n in verif.files.items() }
    verif.files
    
    dims = DIMS['lg']
    pd = verif.files['front'].parent / 'processed'
    pixel_ratio = DIMS['pixel_ratio']
    pd

    for f,tb in [('front21',(100+150,300+550)), ('front22',(100+150,300+550))]:
        debug("main",f, tb)
        locations = DataTree(front=DataTree(top=DataTree(y=tb[0]),bottom=DataTree(y=tb[1])))
        res,fig = process(pd, verif.files[f], DIMS, 'lg', 'front',locations=locations)
        display(Image(fig))
    #     print(res)

# ## Cropping and Measurements




def crop(img, xr, yr):
    xr = np.s_[xr[0]:xr[1]]
    yr = np.s_[yr[0]:yr[1]]
    crop_img = img[yr, xr]
    return crop_img


def saveStep(processedDir, imgName, doSave='save'):
    def saver(stepName, img, dbg=None):
        if doSave == 'save' and processedDir and imgName:
            try:
                path = processedDir / imgName.with_suffix(".{}.png".format(stepName)).name
                pil_img = PIL.Image.fromarray(img_as_ubyte(img))
                pil_img.save(str(path))
                if dbg:
                    dbg.saved_path = path
            except Exception as err:
                print("Error Saving:", img.shape, img.dtype,path.name, path.name, err, flush=True, )

        elif doSave == 'plot':
            plt.imshow(img)
            plt.suptitle(stepName+" "+imgName.name)
            plt.show(block=True)
            plt.close()
        
        return img
            
    return saver




@debugger
def cleanImageOld(img, min_size, scale_factor, img_otsu=None, saver=lambda n,x: x):
    img, exposure_data = normalize_exposure2(img)
    img = saver("01-exposure", img)
    img_otsu = ski.filter.threshold_otsu(img) if not img_otsu else img_otsu
    
    img = saver("02-zoom", scipy.ndimage.zoom(img, scale_factor, order=3))
    print("img:",img.shape,img.dtype)
    
    img_cleaned = saver("03-bw", (img > img_otsu))
    
    dbg = DebugData()   
    
    img_cleaned = morphology.binary_erosion(img_cleaned,
                                            morphology.disk(int(2*scale_factor)))
    
    img_cleaned = saver("04-erosion", img_cleaned, dbg=dbg)
    
    img_cleaned = morphology.remove_small_objects(
                    img_cleaned, min_size=int(min_size*scale_factor), connectivity=2)
                    
    img_cleaned = saver("05-remove", img_cleaned)

    
    cleaned_sum = np.sum(img_cleaned)
    print("img_cleaned size:",cleaned_sum)
    
    return img_cleaned, exposure_data
    



@debugger
def process(processedDir, imgPath, dims, orientation, aspect, locations=None, scale_factor=4, min_size=1000):
    assert orientation in ['lg', 'tr'] 
    assert aspect in ['front', 'side']
    
    if not imgPath or not imgPath.exists():
        return (None, None)

    print(imgPath)
    
    # figname = plotMeasurements(imgPath.name, img_cleaned, img_results_path, img_crop, measures)
    # print("process:",figname)
    
    return measures, figname



def measureWidths(img):
    """ Meausre widths of a sample in a binarized image array. 
    Iterate over rows in binary image 
    Heights=Rows=Vertical 
       - Starting from bottom to top
    Widths=Columns=Horiz
       - Scan rows from left to right

    Find two columns, left most and right most, these are the widths
    """
    idx_horiz,idx_verti,idx_horiz_widths = [],[],[]
    for idx, row in enumerate(reversed(img)):
        indexes = np.where(row[:-1] != row[1:])[0] 
        if len(indexes) == 2: 
            idx_verti.append(idx)
            idx_horiz.append(indexes)
            idx_horiz_widths.append(float(indexes[1]-indexes[0]))

    if not idx_horiz_widths:
        raise Exception("could not find widths: "+str(locals()))
        
    return map(np.array, [idx_verti, idx_horiz, idx_horiz_widths])



def processMeasuredWidths(img, tb):
    x, y, widths = measureWidths(img)
    x_continuous = np.where(x[:-1] != (x[1:]-1))[0]
    x_continuous = [ 0 ] + x_continuous.tolist() + [len(x)-1]
#         debug('orig',[(i,x) for i,x in enumerate(x)])

    max_contiguous_pos = DataTree(idx=0,length=0,start=0,stop=0)
    for idx in range(len(x_continuous)-1):
        stop, start = x_continuous[idx+1],x_continuous[idx]
        length_piece = stop-start
        if max_contiguous_pos.length < length_piece:
            max_contiguous_pos = DataTree(idx=idx, length=length_piece, start=argmax(x,idx=start), stop=argmax(x,idx=stop))

#         debug(x,x_continuous, max_contiguous_pos)

    return DataTree(x=x,y=y,widths=widths, start=max_contiguous_pos.start, stop=max_contiguous_pos.stop)



def processMeasuredWidths2(img, tb):
    debug("processMeasuredWidths2",tb, img.shape, len(img), end=', ')    
    x, y, widths = measureWidths(img[len(img)-int(tb[1]):len(img)-int(tb[0])])
    
#     debug(x,y,widths)
#     debug(x[x>tb[0]])
#     debug(np.where(x>tb[1]))
#     start=argmax(x,idx=np.where(x>len(y)-tb[0])[0][0])
#     stop=argmax(x,idx=np.where(x>len(y)-tb[1])[0][0])
    start=argmax(x,0)
    stop=argmax(x,len(x)-1)
    debug("processMeasuredWidths2",tb, start, stop, len(widths), img.shape, len(y), end=', ')    
    
    assert start is not None 

    assert stop is not None # and stop.idx is not None
    print("tb2", start, stop)
    return DataTree(x=x,y=y,widths=widths, start=start, stop=stop)




def pixelWidths(img_cleaned, pixel_ratio, tb, scale_factor, start=5, stop=-5, **kwargs):
    distance_pixels_avg = pixel_ratio * scale_factor
    tb = (np.array(tb)*scale_factor).tolist()

    print("tb:pixelWidths",tb, img_cleaned.shape, distance_pixels_avg)
    data_px = processMeasuredWidths(img_cleaned,tb)
    print(list(data_px.keys()))
#     debug(data_px.widths[])
    
    data_px.other = DataTree()
    data_px.other.locations = DataTree(top_y=tb[0], bottom_y=tb[1])
    
    data_mm = DataTree(**{k:value for k,value in data_px.items()})
    
    # Take inner third
    start, stop = data_px.start.idx, data_px.stop.idx    
    # Slice measurements
    debug()
    data_mm.x = data_px.x[start:stop]/distance_pixels_avg
    data_mm.y = data_px.y[start:stop]/distance_pixels_avg
    data_mm.widths = data_mm.widths[start:stop]/distance_pixels_avg
    data_mm.other.locations = DataTree(top_y=tb[0]/distance_pixels_avg, bottom_y=tb[1]/distance_pixels_avg)
    data_mm.other.cleaned_data = kwargs['cleaned_data']


    measures = DataTree(px=data_px, mm=data_mm)
    
#     debug(measures.mm.widths)
#     fig, (ax1) = plt.subplots(ncols=3,figsize=(12,6))
#     ax1.imshow(img_cleaned)
    
    def summaryDetails(data):
        third = len(data.widths)//4 - 1
        widths = data.widths[third:-third]
        
        values = DataTree()
        values['mins'] = argmax(data.widths, third+np.argmin(widths))
        values['maxs'] = argmax(data.widths, third+np.argmax(widths))
        values['indexes'] = DataTree(
            idx=(third, len(data.widths)-third),
            value=(widths[third], widths[-third]),
            )
        values['average'] = DataTree(mean=widths.mean(), std=widths.std())
        return DataTree(widths=values)
    
    measures.mm.summaries = summaryDetails(measures.mm)
    
    return measures



def processTest(coun,test):
    
    pd = test.parent / 'processed'
    if not pd.exists(): 
        pd.mkdir()
    
    print(mdHeader(1, "Test {}: {} ({})".format(count,test.info.name, test.info.short()) ) )

    locations = scilab.tools.json.load_json(str(test.parent / 'measured'), json_url="hand.measurements.json")

    orient = test.info.orientation
    pixel_ratio = DIMS['pixel_ratio']
    front, figname1 = process(pd, test.full.front, DIMS,orient,'front', locations)
    fail, figname2 = process(pd, test.full.fail, DIMS,orient,'front', min_size=200, locations=locations)
    side, figname3 = process(pd, test.full.side, DIMS,orient,'side', locations)

    measures = DataTree(front=front,fail=fail,side=side)
    
    for k,measure in measures.items():
        print("## Processing:", k)
        if not measure: continue
#         print("Measurements:\n",flatten(measure.mm.summaries,sep='.'))
    
    scilab.tools.json.write_json(pd, measures)
    summaries = DataTree(**{ k: v.mm.summaries for k,v in measures.items() if v })
    summaries.units = 'mm'
    summaries.info = test.info    
    summariesName = '{}.measurements.json'.format(test.info.name)
    
    scilab.tools.json.write_json(testDataDir, summaries, json_url=summariesName)
    print("Wrote json:", testDataDir)
    
#     clear_output()
    for fig in [figname1, figname2, figname3]:
        if fig:
            fig = (pd/'..'/'..'/fig).resolve()
            
            display(Image(str(fig), width=600))
    


DIMS = {
    "pixel_ratio": DataTree(front=12.492081448,side=13.3873114463, units='mm'),
#     "pixel_ratio": DataTree(front=12.492081448,side=12.492081448, units='mm'),
    'tr': {
        "front": { 'xr':(325,550), 'yr':(300,550) },
        "fail":  { 'xr':(325,550), 'yr':(100,550) },
        "side":  { 'xr':(350,550), 'yr':(300,535) },
    },
    'lg': {
        "front":  { 'xr':(325,550), 'yr':(150,550) },
        "fail":  { 'xr':(325,575), 'yr':(100,550) },
        "side":  { 'xr':(325,525), 'yr':(150,550) },
    },

    'tr-full': { "front": { 'xr':(2325,2550), 'yr':(1300,1550) }, "fail":  { 'xr':(2325,2550), 'yr':(1100,1550) }, "side":  { 'xr':(2350,2550), 'yr':(1365,1535) },
    },
    'lg-full': { "front":  { 'xr':(2325,2550), 'yr':(1250,1550) }, "fail":  { 'xr':(2325,2575), 'yr':(1100,1550) }, "side":  { 'xr':(2325,2525), 'yr':(1250,1550) }, 
                "eraser_rot":  { 'xr':(2025,2775), 'yr':(900,1750) },
    },
    'large-crop': {
        "front": { 'xr':(2000,3000), 'yr':(1000,2000) },
        "fail":  { 'xr':(2000,3000), 'yr':(1000,2000) },
        "side":  { 'xr':(2000,3000), 'yr':(1000,2000) },
    }
}

def handleDirs(testDir):
    fullImgs = { n: next(testDir.glob('cropped-D*.%s.png'%n), None)
                     for n in TestSet._fields }    

    processed = testDir/'processed'

    croppedImgs = { n: next(processed.glob('*.%s.cropped.png'%(n)), None)
                     for n in TestSet._fields }
    cleanedImgs = { n: next(processed.glob('*.%s.cleaned.png'%(n)),None)
                     for n in TestSet._fields }
    
    
    test = DataTree()
    test.parent = testDir
    test.info = UtsTestInfo(name=testDir.name)
    test.full = TestSet(**fullImgs)
    test.cropped = TestSet(**croppedImgs)
    test.cleaned = TestSet(**cleanedImgs)
    
    if not fullImgs or not croppedImgs or not cleanedImgs:
        raise Exception("Missing files: "+testDir)

    return test


def handleDirs(testDir):
    fullImgs = { n: next(testDir.glob('cropped-D*.%s.png'%n), None)
                     for n in TestSet._fields }    

    processed = testDir/'processed'

    croppedImgs = { n: next(processed.glob('*.%s.cropped.png'%(n)), None)
                     for n in TestSet._fields }
    cleanedImgs = { n: next(processed.glob('*.%s.cleaned.png'%(n)),None)
                     for n in TestSet._fields }
    
    test = DataTree()
    test.parent = testDir
    test.info = UtsTestInfo(name=testDir.name)
    test.large = TestSet(**fullImgs)
    
    if not fullImgs or not croppedImgs or not cleanedImgs:
        raise Exception("Missing files: "+testDir)

    return test


def processTest(coun,test):
    
    pd = test.parent / 'processed'
    if not pd.exists(): 
        pd.mkdir()
    
    print(mdHeader(1, "Test {}: {} ({})".format(count,test.info.name, test.info.short()) ) )

    locations = scilab.tools.json.load_json(str(test.parent / 'measured'), json_url="hand.measurements.json")

    orient = test.info.orientation
    pixel_ratio = DIMS['pixel_ratio']
    front, figname1 = process(pd, test.full.front, DIMS,orient,'front', locations)
    fail, figname2 = process(pd, test.full.fail, DIMS,orient,'front', min_size=200, locations=locations)
    side, figname3 = process(pd, test.full.side, DIMS,orient,'side', locations)

    measures = DataTree(front=front,fail=fail,side=side)
    
    for k,measure in measures.items():
        print("## Processing:", k)
        if not measure: continue
    
    scilab.tools.json.write_json(pd, measures)
    summaries = DataTree(**{ k: v.mm.summaries for k,v in measures.items() if v })
    summaries.units = 'mm'
    summaries.info = test.info    
    summariesName = '{}.measurements.json'.format(test.info.name)
    
    scilab.tools.json.write_json(testDataDir, summaries, json_url=summariesName)
    print("Wrote json:", testDataDir)
    
    for fig in [figname1, figname2, figname3]:
        if fig:
            fig = (pd/'..'/'..'/fig).resolve()
            
            display(Image(str(fig), width=600))
    

def runSpecimen():
    
    imagesDirs = [ handleDirs(f) for f in WORKING_DIR.glob('*') if f.is_dir() ]
    imagesDirs[0]

    RUN = True
    failed = {}
    if RUN:
        for count, test in enumerate(imagesDirs[0:1]):
            try:
                processTest(count,test)
            except Exception as err:
                logging.warn(err)
                failed[test.info.name] = err
                raise err



    print(failed) 

    len(imagesDirs)


def main():
    
    if 'PARENT_DIR' not in locals():
        NOTEBOOK_DIR = Path(os.curdir).resolve() 
        PARENT_DIR = Path(os.curdir) / '..' 
        PARENT_DIR = PARENT_DIR.resolve()
        print("Setting:\n",PARENT_DIR)
    else:
        print("Parent Dir configured as:\n", PARENT_DIR)

    DEBUG = True 
    testDataDir = PARENT_DIR/'test-data'/'uts (expr-1)'/'00 JSON'
    if not testDataDir.exists(): 
        testDataDir.mkdir()


    WORKING_DIR = PARENT_DIR / "05 Specimen Images" / "02 Test Images"
    if 'WORKING_DIR_FULL' not in locals():
        os.chdir(str(WORKING_DIR.resolve()))
        WORKING_DIR = Path('.')
    WORKING_DIR_FULL = WORKING_DIR.resolve()
    WORKING_DIR_FULL




if __name__ == '__main__':
    main()
