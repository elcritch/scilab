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
from PIL import Image as PILImage

def processimg(img, scale, max_width,
                gamma, gain, img_otsu, 
               remove_small, remove_small_pre, 
               min_size, auto_otsu, equalize_adapthist,
               erode_pixels, 
               zoomfactor,
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

    if erode_pixels and erode_pixels > 0:
        print("Eroding binary image: ", erode_pixels)
        img_bw = morphology.binary_erosion(img_bw, morphology.disk(int(erode_pixels)))
    
    
    if remove_small:
        img_bw = morphology.remove_small_objects(img_bw, min_size=min_size, connectivity=2)
    
    
    return DataTree(image=img, adjusted=image, binarized=img_bw)

def argvaluechanges(data):
    indices = (np.where(data[:-1] != data[1:])[0]).astype(int)
    return indices

def samplemeasurement(scale, img_bw):
    
    hori_indices = argvaluechanges(np.sum(img_bw, 0) > 0)
    vert_indices = argvaluechanges(np.sum(img_bw, 1) > 0)
    debug(hori_indices, vert_indices, np.sum(img_bw, 0) > 0)
    assert len(vert_indices) >= 2
    
    top, bottom = vert_indices[0], vert_indices[-1]
    left, right = hori_indices[0], hori_indices[-1]
    vsize, hsize = bottom-top, right-left
    boundingbox = DataTree(top=top, left=left, right=right, bottom=bottom, units="px")
    
    def calcwidths(arr):
        widths = (np.sum(arr, 1))/scale.value
        return valueUnitsStd(np.mean(widths), stdev=np.std(widths), units="mm")._asdict()
    
    measurements = DataTree()
    measurements.boundingbox = boundingbox
    
    measurements["raw","widths"] = calcwidths(img_bw[top:bottom])
    measurements["thirds", "upper"]  = calcwidths(img_bw[top+0*vsize//3:top+1*vsize//3])
    measurements["thirds", "middle"] = calcwidths(img_bw[top+1*vsize//3:top+2*vsize//3])
    measurements["thirds", "lower"]  = calcwidths(img_bw[top+2*vsize//3:top+3*vsize//3])
    
    return measurements

def crop(img, xd, yd, **kws):
    xd_ = np.s_[xd[0]:xd[1]]
    yd_ = np.s_[yd[0]:yd[1]]
    debug(xd, yd, img.shape)
    crop_img = img[yd_, xd_]
    debug(crop_img.shape)
    return crop_img

def process_image(testconf, imagepath, scaling, cropping, zoomfactor, imageconf, state, args):
    
    processingconfs = DataTree(
                max_width=2.0, # e.g. mm (converted to pixels during processing)
                gamma=1.0, 
                gain= 1.0, 
                img_otsu=0.14,  
                remove_small=True, 
                remove_small_pre=True,
                min_size=1000*zoomfactor,
                auto_otsu=True,
                equalize_adapthist=True,
                erode_pixels=1, # 1 pixel of erosion at 2*zoom yields good avg of extra pixel gained during binarization/measurement
                )
    
    # The cropped image will be "zoomed" so adjust the scaling factor appropriately
    debug(zoomfactor)
    
    if testconf['options','processing']:
        processingconfs.update(testconf['options','processing'])
    
    def getimagepath(stage):
        return state.processed / "{name}.{stage}.png".format(name=imageconf["name"], stage=stage)
    
    croppedimage = getimagepath(stage="cropped")
    debug(croppedimage)
    
    if not imagepath.exists():
        raise ValueError("Image file not found: "+str(imagepath), imageconf)
    
    if not croppedimage.exists() or args["force", "imagecaching"]:
        print("Cropping and caching image")
        img = loadimage(imagepath=imagepath)
        debug(img.shape)
        imgout = crop(img, **cropping)
        imgout = scipy.ndimage.zoom(imgout, (zoomfactor, zoomfactor, 1), order=3)
        debug(imgout.shape)
        saveimage(imgout, croppedimage)
    
    image = loadimage(croppedimage)
    processedimages = processimg(image, scale=scaling, zoomfactor=zoomfactor, **processingconfs)
    
    saveimage(processedimages.adjusted, getimagepath("adjusted"))
    saveimage(processedimages.binarized, getimagepath("binarized"))
    
    return processedimages
        
def process_imageconf(testconf, imageconf, state, args):
    
    # Image Measurement Scaling
    zoomfactor = state["image_measurement"].get("zoomfactor", 2)
    scaling = getproperty(state["image_measurement"]["scales"], action=True, env=state)
    scaling = scaling.set(value=scaling.value*zoomfactor)
    
    # Image Cropping
    cropping = state.image_measurement["crops"]
    while isinstance(cropping, collections.Mapping) and '_lookup_' in cropping:
        cropping = getproperty(cropping, action=True, env=state)
        debug(cropping)
        
    # === Process Image === 
    processedFolder = testconf.folder.images / 'processed'
    
    if not processedFolder.exists():
        os.mkdir(str(processedFolder))
        
    if not imageconf["name"] in testconf.folder.keys():
        raise ValueError("Missing file in projdesc.json configuration. ", imageconf)
    
    imagepath = builtin_action_resolve(testconf.folder[imageconf["name"]], env=state)

    print("Processing Image Measurements from: ", imagepath)
    imageprocessstate = state.set(imagepath=imagepath, processed=processedFolder)
    
    processedimages = process_image(testconf, imageconf=imageconf, imagepath=imagepath, scaling=scaling, cropping=cropping, zoomfactor=zoomfactor, 
                                    state=imageprocessstate, args=args)
    measurements = samplemeasurement(scaling, processedimages.binarized)
    measurements["parameters", "scale"] = scaling  
    measurements["parameters", "zoomfactor"] = valueUnits(100*zoomfactor, units='%')._asdict()
    
    debug(measurements)
    
    jsonpath, allmeasurements = testconf.folder.save_calculated_json(
        test=state.args.testconf, 
        name="measurements",
        field="images",
        data={ imageconf["name"]: measurements },
        )

    return allmeasurements

def process_test(testconf, state, args):
    
    image_measurement = state["image_measurement"]
    
    testconf.folder.save_calculated_json(test=state.args.testconf, name="measurements",field="images",data={},overwrite=True)
    
    for imageconf in image_measurement["imageconfs"]:
        
        imagestate = state.set(imagename=imageconf.name, imageconf=imageconf)
        push(imagestate, 'imageconf', imageconf.name)
        allmeasurements = process_imageconf(testconf, imageconf=imageconf, state=imagestate, args=args)
    
    env=calcenv()
    results = DataTree()
    for calcname, calcs in image_measurement["calculations",].items():
        for calc in calcs:
            name, calcexpr = getpropertypair(calc)
            debug(name, calcexpr)
            result = executeexpr(calcexpr, results=results, calc=env, **allmeasurements["measurements"])
            debug(result)
            results[calcname, name] = result

    testconf.folder.save_calculated_json(data=results, test=state.args.testconf, name="measurements", field="images")

