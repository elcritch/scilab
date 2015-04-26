import os, sys, functools, itertools, collections, re, logging
from pathlib import *
from tabulate import *

import scilab, scilab.tools.jsonutils
from scilab.tools.project import *
from scilab.datahandling.datahandlers import *

import scipy.misc
import scipy, scipy.ndimage as ndimage
import skimage as ski, skimage.io as io, skimage.feature as feature, skimage.morphology as morphology, skimage.filter as imgfilter
from skimage.util import img_as_ubyte

def processimg(img, scale, max_width,
                gamma, gain, img_otsu, 
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
    img_valid_widths = np.array(img_bw_lens(img_bw) < max_width*scale.value, dtype='int') * \
                            np.array(np.sum(img_bw,1) < max_width*scale.value, dtype='int') 
                            
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
        print("Loading image: ", str(imagepath))
        # img_raw = io.imread(str(imagepath))
        img_raw = scipy.ndimage.imread(str(imagepath))
        debug(img_raw.shape, img_raw.dtype)
        return ski.img_as_ubyte(img_raw)
        # return io.imread(str(imagepath))
    except Exception as err:
        raise err
        # raise Exception("Error loading image: "+str(imagepath), imageconf, err)

def saveimage(image, imagepath, imageconf):
    try:
        return scipy.misc.imsave(str(imagepath), image)
    except Exception as err:
        raise Exception("Error loading image: "+imagepath, imageconf, err)
    
def crop(img, xd, yd, **kws):
    xd_ = np.s_[xd[0]:xd[1]]
    yd_ = np.s_[yd[0]:yd[1]]
    debug(xd, yd, img.shape)
    crop_img = img[yd_, xd_]
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
        return state.processed / "{name}.{stage}.png".format(name=imageconf["name"], stage=stage)
    
    croppedimage = getimagepath(stage="cropped")
    debug(croppedimage)
    
    if not imagepath.exists():
        raise ValueError("Image file not found: "+str(imagepath), imageconf)
    
    if not croppedimage.exists():
        print("Cropping and caching image")
        img = loadimage(imagepath=imagepath, imageconf=imageconf)
        debug(img.shape)
        img_crop = crop(img, **cropping)
        saveimage(img_crop, croppedimage, imageconf)
    
    image = loadimage(croppedimage, imageconf)
    processedimages = processimg(image, scale=scaling, **processingconfs)
    
    saveimage(processedimages.adjusted, getimagepath("adjusted"), imageconf=imageconf)
    saveimage(processedimages.binarized, getimagepath("binarized"), imageconf=imageconf)
    
def process_imageconf(testconf, imageconf, state, args):
    
    # Image Measurement Scaling
    scaling = getproperty(state["image_measurement"]["scales"], action=True, env=state)
    
    # Image Cropping
    cropping = state.image_measurement["crops"]
    while isinstance(cropping, collections.Mapping) and '_lookup_' in cropping:
        cropping = getproperty(cropping, action=True, env=state)
        debug(cropping)
        
    # === Process Image === 
    processedFolder = testconf.folder.images / 'processed'
    if not imageconf["name"] in testconf.folder.keys():
        raise ValueError("Missing file in projdesc.json configuration. ", imageconf)
    
    imagepath = builtin_action_resolve(testconf.folder[imageconf["name"]], env=state)

    print("Processing Image Measurements from: ", imagepath)
    imageprocessstate = state.set(imagepath=imagepath, processed=processedFolder)
    
    process_image(testconf, imageconf=imageconf, imagepath=imagepath, scaling=scaling, cropping=cropping, state=imageprocessstate, args=args)    

def process_test(testconf, state, args):
    
    image_measurement = state["image_measurement"]
        
    for imageconf in image_measurement["imageconfs"]:
        
        imagestate = state.set(imagename=imageconf.name, imageconf=imageconf)
        push(imagestate, 'imageconf', imageconf.name)
        process_imageconf(testconf, imageconf=imageconf, state=imagestate, args=args)
    