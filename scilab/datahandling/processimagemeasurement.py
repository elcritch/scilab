import os, sys, functools, itertools, collections, re, logging
from pathlib import *
from tabulate import *

import scilab, scilab.tools.jsonutils
from scilab.tools.project import *

import scipy.misc.imsave 
import scipy, scipy.ndimage as ndimage
import skimage as ski, skimage.io as io, skimage.feature as feature, skimage.morphology as morphology, skimage.filter as imgfilter
from skimage.util import img_as_ubyte

def processimg(img, scale, max_width,
                gamma, gain, ricis_factor, img_otsu, sobel_otsu,
               remove_small, remove_small_pre, 
               min_size, auto_otsu, equalize_adapthist,
               ):
    image = np.copy(img[:,:,0])
    
    image = ski.exposure.adjust_gamma(image, gamma=gamma, gain=gain)
    
    if equalize_adapthist:
        image = ski.exposure.equalize_adapthist(image)
    
    # ============================
    # = Binarize the input image =
    # ============================
    
    if auto_otsu:
        img_otsu = imgfilter.threshold_otsu(image)

    img_bw = (image > img_otsu)
    
    if remove_small_pre:
        img_bw = morphology.remove_small_objects(img_bw, min_size=min_size, connectivity=2)

    # =============================================================
    # = Calculate regions which satisfy the region area containts =
    # =============================================================
    
    img_bw_lens = lambda aa: aa.shape[1] - np.argmax( aa[:, ::-1] > 0, 1 ) - np.argmax( aa > 0, 1)
    
    # check for both start/end of objects AND the total area
    img_valid_widths = np.array(img_bw_lens(img_bw) < max_width*scale, dtype='int') *
                            np.array(np.sum(img_bw,1) < max_width*scale, dtype='int') 
                            
    img_bw = np.array([ r*s for r, s in zip(img_bw, img_valid_widths) ], dtype=img_bw.dtype)

    if remove_small:
        img_bw = morphology.remove_small_objects(img_bw, min_size=min_size, connectivity=2)
    
    return DataTree(image=img, adjusted=image, binarized=img_bw)

def argvaluechanges(data):
    indices = (np.where(data[:-1] != data[1:])[0]).astype(int)
    return indices

def samplemeasurement(scale, img_bw):
    
    hori_indices = argvaluechanges(np.where(np.sum(img_bw, 0) > 0))
    vert_indices = argvaluechanges(np.where(np.sum(img_bw, 1) > 0))
    assert len(vert_indices) >= 2
    
    top, bottom = vert_indices[0], vert_indices[-1]
    left, right = hori_indices[0], hori_indices[-1]
    vsize, hsize = top-bottom, right-left
    boundingbox = DataTree(top=top, left=left, right=right, bottom=bottom, units="px")
    
    def calcwidths(arr):
        widths = (np.sum(arr, 1))/scale
        return valueUnits(widths, np.std(widths), units="mm")
    
    measurements = DataTree()
    measurements.boundingbox = boundingbox
    measurements.length = valueUnits((boundingbox.top-boundingbox.bottom)/scale, units="mm")
    
    measurements.widths = calcwidths(img_bw[top:bottom])
    measurements["thirds", "upper"]  = calcwidths(img_bw[top+0*vsize//3:top+1*vsize//3])
    measurements["thirds", "middle"] = calcwidths(img_bw[top+1*vsize//3:top+2*vsize//3])
    measurements["thirds", "lower"]  = calcwidths(img_bw[top+2*vsize//3:top+3*vsize//3])
    
    return measurements

def loadimage(imagepath, imageconf):
    try:
        return ski.img_as_ubyte(skimage.io.imread(str(imagepath)))    
    except Exception as err:
        raise Exception("Error loading image: "+imagepath, imageconf, err)

def saveimage(image, imagepath, imageconf):
    try:
        return scipy.misc.imsave(str(imagepath), image)
    except Exception as err:
        raise Exception("Error loading image: "+imagepath, imageconf, err)
    
def crop(img, xr, yr):
    xr = np.s_[xr[0]:xr[1]]
    yr = np.s_[yr[0]:yr[1]]
    crop_img = img[yr, xr]
    return crop_img

def process_image(testconf, imagepath, scaling, cropping, imageconf, state, args):
    
    processingconfs = DataTree(
                max_width=2.0, # e.g. mm (converted to pixels during processing)
                gamma=1.0, 
                gain= 1.0, 
                img_otsu=0.14,  
                remove_small=True, 
                remove_small_pre=True,
                min_size=1000,
                auto_otsu=True,
                equalize_adapthist=True,
                )
        
    if testconf['options','processing']:
        processingconfs.update(testconf['options','processing'])
    
    def getimagepath(stage):
        croppedimage = state.processed / "{name}.{stage}.png".format(name=imageconf["name"], stage=stage)
    
    croppedimage = getimagepath(stage="cropped")
    debug(croppedimage)
    
    if not imagepath.exists():
        raise ValueError("Image file not found: "+str(imagepath), imageconf)
        
    if note croppedimage.exists():
        print("Cropping and caching image")
        img = loadimage(imagepath)
        img_crop = crop(img, **cropping)
        saveimage(img_crop, croppedimage, imageconf)
    
    image = loadimage(croppedimage)
    processedimages = processimg(image, scale=scaling, **processingconfs)
    
    saveimage(processedimages.adjusted, getimagepath("adjusted"))
    saveimage(processedimages.binarized, getimagepath("binarized"))
    
def process_imageconf(testconf, imageconf, state, args):
    
    # Image Measurement Scaling
    scaling = getproperty(imageconf["scales"], action=True, env=state)
    
    # Image Cropping
    cropping = imageconf["crops"]
    while isinstance(cropping, collections.Mapping) and '_lookup_' in cropping:
        cropping = getproperty(cropping, action=True, env=state)
        debug(cropping)
        
    # === Process Image === 
    
    processedFolder = testconf.folder.images / 'processed'
    if not imagename in testconf.folder.keys():
        raise ValueError("Missing file in projdesc.json configuration. ", imageconf)
    
    imagepath = builtin_action_resolve(testconf.folder[imagename])
    print("Processing Image Measurements from: ", imagepath)
    imageprocessstate = state.set(imagepath=imagepath, processed=processedFolder)
    
    process_image(testconf, imagepath=imagepath, scaling=scaling, cropping=cropping, state=imageprocessstate, args=args)    

def process_test(testconf, state, args):
    
    imageconfs = state["imageconfs"]
        
    for imageconf in imageconfs:
        
        imagestate = state.set(imagename=imageconf.name, imageconf=imageconf)
        push(imagestate, 'imageconf', imageconf.name)
        process_imageconf(testconf, imageconf=imageconf, state=imagestate, args)
    