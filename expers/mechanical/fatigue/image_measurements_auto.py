
# coding: utf-8

# In[1]:

import os, sys, functools, itertools, collections, re, logging
from pathlib import *
from tabulate import *


# In[2]:

# import matplotlib; matplotlib.use('MacOSX')

get_ipython().magic('matplotlib inline')
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display
import numpy as np, scipy


# In[3]:

import scilab, scilab.tools.graphing, scilab.tools.json 
from scilab.tools.project import *
from scilab.expers.mechanical.fatigue.uts import *


# In[4]:

def argmax(y,idx):
    return DataTree(idx=idx, value=y[idx])


# In[5]:

if 'PARENT_DIR' not in locals():
    NOTEBOOK_DIR = Path(os.curdir).resolve() 
    PARENT_DIR = Path(os.curdir) / '..' 
    PARENT_DIR = PARENT_DIR.resolve()
    print("Setting:\n",PARENT_DIR)
else:
    print("Parent Dir configured as:\n", PARENT_DIR)


# In[6]:

WORKING_DIR = PARENT_DIR / "05 Specimen Images" / "02 Test Images"
if 'WORKING_DIR_FULL' not in locals():
    os.chdir(str(WORKING_DIR.resolve()))
    WORKING_DIR = Path('.')
WORKING_DIR_FULL = WORKING_DIR.resolve()
WORKING_DIR_FULL


# In[7]:

TestSet = collections.namedtuple('TestSet', 'front, side, fail')

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

imagesDirs = [ handleDirs(f) for f in WORKING_DIR.glob('*') if f.is_dir() ]
imagesDirs[0]


# In[8]:

from scilab.tools.tables import mdBlock, mdHeader, ImageTable, MarkdownTable
from functools import partial 


# In[9]:

def mapTo(func, iterable,*args,**kwargs):
    return [ (i, func(i,*args,**kwargs)) for i in iterable ]


# In[10]:


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



# In[11]:

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


# ## Cropping and Measurements
# 

# In[12]:

import scipy, scipy.ndimage as ndimage
import skimage as ski, skimage.io as io, skimage.feature as feature, skimage.morphology as morphology
import scipy.ndimage as ndimage
from skimage.data import data_dir; from skimage.util import img_as_ubyte; from skimage import io


# In[13]:

from IPython.display import *


# In[14]:

def crop(img, xr, yr):
    xr = np.s_[xr[0]:xr[1]]
    yr = np.s_[yr[0]:yr[1]]
    crop_img = img[yr, xr]
    return crop_img


# In[15]:

import PIL.Image

def saveStep(processedDir, imgName, doSave='save'):
    def saver(stepName, img, dbg=None):
        if doSave == 'save' and processedDir and imgName:
            try:
                path = processedDir / imgName.with_suffix(".{}.png".format(stepName)).name
#                 print("Saving:", img.shape, img.dtype,path.name, path.name, flush=True, )
                pil_img = PIL.Image.fromarray(img_as_ubyte(img))
                pil_img.save(str(path))
#                 print("Saved:", img.shape, img.dtype,path.name, path.name, flush=True, )
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


# In[16]:

def PIL2array(img):
    return np.array(img.getdata(), np.uint8).reshape(img.size[1], img.size[0], 3)


# In[17]:

def normalize_exposure(img, factor=1.0, clip_limit=0.1, **kwargs):
    img_orig = img
    if True:
        return img_orig
    
    img = ski.exposure.equalize_hist(img)
    
    fig, ax = plt.subplots(ncols=2,nrows=3,figsize=(12,6))
    ax[0,0].hist(ski.exposure.histogram(img_orig,128),bins=128)
    ax[0,1].hist(ski.exposure.histogram(img,128),bins=128)
    ax[1,0].imshow(img_orig)
    ax[1,1].imshow(img)
    ax[2,0].plot(np.arange(img_orig.shape[0]),np.array([sum(r[:,0]) for r in img_orig ] ))
    ax[2,1].plot(np.arange(img_orig.shape[2]),np.array([sum(r[:,0]) for r in img_orig.T ] ))

    #     plt.hold(True)
    return img


# In[18]:

def cleanImage(img, min_size, scale_factor, img_otsu=None, saver=lambda n,x: x):
    img, exposure_data = normalize_exposure2(img)
    img = saver("01-exposure", img)
    img_otsu = ski.filter.threshold_otsu(img) if not img_otsu else img_otsu
    print('otsu:',img_otsu, ski.filter.threshold_otsu(img))
    
    img = saver("02-zoom", scipy.ndimage.zoom(img, scale_factor, order=3))
    print("shape after zoom:", img.shape)
#     img_pil = PIL.Image.fromarray(img).resize((np.array(img.shape)*scale_factor).tolist()[:2], resample=PIL.Image.BICUBIC)
#     img = saver("02-zoom", PIL2array(img_pil))
    print("img:",img.shape,img.dtype)
    
    img_cleaned = saver("03-bw", (img > img_otsu))
#     img_cleaned = saver("03-bw", (img > 0.2))
    
    dbg = DebugData()   
    
    img_cleaned = morphology.binary_erosion(img_cleaned,morphology.disk(int(2*scale_factor)))
    img_cleaned = saver("04-erosion", img_cleaned, dbg=dbg)
    
    img_cleaned = morphology.remove_small_objects(img_cleaned, min_size=int(min_size*scale_factor), connectivity=2)
    img_cleaned = saver("05-remove", img_cleaned)

    
    cleaned_sum = np.sum(img_cleaned)
    print("img_cleaned size:",cleaned_sum)
#     if cleaned_sum < 1000 or cleaned_sum > 300000:
#         display(Image(str(dbg.saved_path)))
#         raise Exception("Image not cleaned correctly"+str(locals()))
    
    return img_cleaned, exposure_data
    


# # Jump

# In[60]:

def normalize_exposure3(img, factor=1.0, clip_limit=0.1, **kwargs):
    img_orig = img
    
    img = np.average(img, axis=2)
    
    exposureAvg = np.average(img)
    targetAverage = 50.0
    debug(exposureAvg, targetAverage)

    calcExposure = lambda f: np.average(img*f)
    f = 0.05
    while calcExposure(f) < targetAverage:
        f += 0.05
        
    debug(f, calcExposure(f))
#     img = img*f
    
    img = ski.exposure.adjust_gamma(img, gamma=1.6, gain=1)
#     img = ski.exposure.adjust_gamma(img, gamma=2.6, gain=1)
    img_gamma=img
    
    middle = img.shape[0]/2
    middleSection = img[middle:middle+10]
#     maxAvgIntensity = np.max(np.average(middleSection, axis=0))
    
    debug(maxAvgIntensity)
    img = img/maxAvgIntensity * 0.4

    hist = scipy.ndimage.measurements.histogram(img[middle:middle+10], 0,1, 100)
    hist = np.array([ (n*1/100,i, n) for n,i in enumerate(hist) ])
    histMax = argmax(hist, np.argmax(hist[:,1]))
#     print('\n'.join(map(str,hist[:20])))
#     maxBase = np.where(hist[histMax.idx:][:,1] < np.average(hist))[0][0] + histMax.idx + 2
#     print("Max of Base values:", hist[maxBase][0], np.average(hist))
#     img = ski.exposure.equalize_adapthist (img)
#     img_gamma=img

#     fig, ax = plt.subplots(ncols=2,nrows=1,figsize=(12,6))
#     ax[0].plot(np.arange(img.shape[1]), np.average(img[middle:middle+10], axis=0))
#     ax[1].imshow(img)
#     ax[0].set_ylim(ymax=1.0)
    
#     plt.show()
    print("normalize:", img.shape)
    #     plt.hold(True)
    return img, DataTree()


# In[61]:

def normalize_exposure2(img, factor=1.0, clip_limit=0.1, **kwargs):
    img_orig = img
    
    img = np.average(img, axis=2)
    
    exposureAvg = np.average(img)
    targetAverage = 50.0
    debug(exposureAvg, targetAverage, np.max(img))

    calcExposure = lambda f: np.average(img*f)
    f = 0.05
    while calcExposure(f) < targetAverage:
        f += 0.05
        
    debug(f, calcExposure(f))
#     img = img*f
    
    img = ski.exposure.adjust_gamma(img, gamma=1.6, gain=1)
#     img = ski.exposure.adjust_gamma(img, gamma=2.6, gain=1)
    img_gamma=img
    
    middle = img.shape[0]/2
    middleSection = img[middle:middle+20]
    maxAvgIntensity = np.max(np.average(middleSection, axis=0))
    
    debug(maxAvgIntensity)
    img = img/maxAvgIntensity * 0.5

    maxAvgIntensityScaled = np.max(np.average(img[middle:middle+10], axis=0))

    hist = scipy.ndimage.measurements.histogram(img[middle:middle+10], 0,1, 100)
    hist = np.array([ (n*1/100,i, n) for n,i in enumerate(hist) ])
    histMax = argmax(hist, np.argmax(hist[:,1]))
#     print('\n'.join(map(str,hist[:20])))
    maxBase = np.where(hist[histMax.idx:][:,1] < np.average(hist))[0][0] + histMax.idx + 2
    print("Max of Base values:", hist[maxBase][0], np.average(hist))
#     img = ski.exposure.equalize_adapthist (img)
#     img_gamma=img

    fig, ax = plt.subplots(ncols=2,nrows=1,figsize=(12,6))
    ax[0].plot(np.arange(img.shape[1]), np.average(img[middle:middle+10], axis=0))
    ax[1].imshow(img)
#     ax[0].set_ylim(ymax=1.0)
    
    plt.show()
    print("normalize:", img.shape)
    #     plt.hold(True)
    return img, DataTree(maxAvgIntensity=maxAvgIntensity, maxAvgIntensityScaled=maxAvgIntensityScaled, exposureAvg=exposureAvg, )


# In[21]:

def locationsToTB(img_shape, img_crop_shape, locations, crops):
    debug(locals())
    y_bottom, y_top = locations['bottom']['y'], locations['top']['y']
    if y_bottom > y_top:
        y_bottom, y_top = y_top, y_bottom
    image_top = (img_shape[0]-crops['yr'][1])
    print("cropping top/bottom:", y_top, y_bottom, img_shape, img_crop_shape)
    
    debug(img_shape[0]-crops['yr'][1], img_shape[1]-crops['yr'][1])
    return (image_top-y_top, image_top-y_bottom)


# In[22]:

def process(processedDir, imgPath, dims, orientation, aspect, locations=None, scale_factor=4, min_size=1000):
#     plt.hold(False)

    assert orientation in ['lg', 'tr'] 
    assert aspect in ['front', 'side']
    
    if not imgPath or not imgPath.exists():
        return (None, None)

    print("Processing:",imgPath.name)
    print("output dir:", processedDir)
    saver = saveStep(processedDir, imgPath,doSave='save')
    
    img = ski.img_as_ubyte(io.imread(str(imgPath)))
    img_crop = crop(img, **dims[orientation][aspect])
    saver("cropped", img_crop)
    
#     for otsu in np.arange(0.05,0.6,0.05):
#         img_cleaned = cleanImage(img_crop, img_otsu=otsu, min_size=min_size, scale_factor=scale_factor,saver=saver)
#         img_cleaned_sum = np.sum(img_cleaned)
#         plt.imshow(img_cleaned)
#         plt.suptitle("cleaned-"+str(otsu))
#         plt.show()
#         plt.close()
        
#         if img_cleaned_sum < 1E4:
#             break

    img_cleaned, cleaned_data = cleanImage(img_crop, min_size=min_size, scale_factor=scale_factor,saver=saver)
    saver("cleaned", img_cleaned)
    
#             "front": { 'xr':(325,550), 'yr':(300,550) },
    tb = locationsToTB(img.shape, img_crop.shape, locations[aspect], dims[orientation][aspect])
    debug('process:',tb)
    
    img_results_path = processedDir / imgPath.with_suffix(".results.png" ).name
    measures = pixelWidths(img_cleaned,dims['pixel_ratio'][aspect], tb=tb, 
                           scale_factor=scale_factor, cleaned_data=cleaned_data)
    
    figname = plotMeasurements(imgPath.name, img_cleaned, img_results_path, img_crop, measures)
    print("process:",figname)
    return measures, figname


# In[23]:

for f,tb in [('front21',(100+150,300+550)), ('front22',(100+150,300+550))]:
    debug("main",f, tb)
    locations = DataTree(front=DataTree(top=DataTree(y=tb[0]),bottom=DataTree(y=tb[1])))
    res,fig = process(pd, verif.files[f], DIMS, 'lg', 'front',locations=locations)
    display(Image(fig))
#     print(res)


# In[24]:

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


# In[25]:

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


# In[54]:

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


# In[56]:


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


# In[35]:




# In[36]:

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

# In[29]:

def flatten(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


# In[30]:

DEBUG = True 
testDataDir = PARENT_DIR/'test-data'/'uts (expr-1)'/'00 JSON'
if not testDataDir.exists(): 
    testDataDir.mkdir()

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
    


# In[62]:

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


# In[ ]:

failed 


# In[ ]:

len(imagesDirs)


# ## Verification 

# # Jump

# In[ ]:

front, figname1 = process(pd, verif.files['front'], DIMS, orientation='lg', aspect='front', locations)
display(Image(figname1))


# In[ ]:

for f in ['front21', 'front22','front23']:
    display(Image(process(pd, verif.files[f], DIMS, 'lg', 'front')[1]))


# In[ ]:

side, figname2 = process(pd, verif.files['side'], DIMS, 'lg','side')
display(Image(figname2))


# In[ ]:

pp = lambda p: [ '{:.2f} mm'.format(i) for i in p]
ppp = lambda p: [ '{:.2f} % mm'.format(i) for i in p]


# In[ ]:

paperclip_measure = np.array([ 1.19, 1.23 ])
paperclip_true = 1.15
print("Paper clip: 1.15mm true" )
print("   Results (front, side):\t",pp(paperclip_measure))
print("Ratio Diff (front, side):\t",pp( (paperclip_measure)/paperclip_true ))
print(" Perc Diff (front, side):\t",ppp((paperclip_measure-paperclip_true)/paperclip_true*100))


# In[ ]:

dims = DIMS['lg']
pixel_ratio = DIMS['pixel_ratio']
front, figname1 = process(pd, verif.files['front_eraser'], dims, pixel_ratio.front,'front')
side, figname2 = process(pd, verif.files['side_eraser'], dims, pixel_ratio.side,'side')
display(Image(figname1), Image(figname2))


# In[ ]:

eraser_measure = np.array([7.08, 6.66])
eraser_true = 6.79

print("Eraser: 6.79 mm true" )
print("   Results (front, side):\t",pp(eraser_measure))
print("Ratio Diff (front, side):\t",pp( (eraser_measure)/eraser_true ))
print(" Perc Diff (front, side):\t",ppp((eraser_measure-eraser_true)/eraser_true*100))


# In[ ]:

frontRot, figname1rot = process(pd, verif.files['front_eraser_rot'], dims, pixel_ratio.front,'eraser_rot')
display(Image(figname1rot))


# In[ ]:




# In[ ]:

def plotAllImages(image_dict, vert=False):
    ncols, nrows =  (1, len(image_dict)) if vert else (len(image_dict), 1)
    fig, axes = plt.subplots(ncols=ncols, nrows=nrows, figsize=(18,14))
    for (name, image), ax in zip(image_dict, axes):
        ax.imshow(image)
        ax.set_title(name)
#         ax.axis('off')


# In[ ]:




# In[ ]:




# In[ ]:

print()

