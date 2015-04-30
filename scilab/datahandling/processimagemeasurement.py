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
               dbg=False,
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
    dbg and print("Removing rows less wide than zoomed max width (max_width*scale)", max_width*scale.value, max_width, scale.value)
    
    img_valid_widths = np.array(img_bw_lens(img_bw) < max_width*scale.value, dtype='int') * \
                            np.array(np.sum(img_bw,1) < max_width*scale.value, dtype='int') 
                            
    dbg and print( "sum before:", np.sum(img_bw, 1))
    
    img_bw = np.array([ r*s for r, s in zip(img_bw, img_valid_widths) ], dtype=img_bw.dtype)

    dbg and print( "sum after:", np.sum(img_bw, 1))
    
    if erode_pixels and erode_pixels > 0:
        dbg and print("Eroding binary image: ", erode_pixels)
        img_bw = morphology.binary_erosion(img_bw, morphology.disk(int(erode_pixels)))
    
    dbg and print( "sum after erode:", np.sum(img_bw, 1))
        
    # = Reconvert back to boolean! =
    img_bw = img_bw.astype('bool')
    
    if remove_small:
        dbg and print("Removing small features less than: ", min_size)
        img_bw = morphology.remove_small_objects(img_bw, min_size=min_size, connectivity=1)
    
    
    # img_bw = img_bw*255 # scaling??
    dbg and print( "sum after remove small:", np.sum(img_bw, 1))
    
    # = Reconvert back to boolean! (Just in case... this has a tendency to revert after various ops causing issues) =
    img_bw = img_bw.astype('bool')
    
    if np.sum(img_bw) < min_size:
        
            raise ValueError("Binarized image below minimum size! Sum: ", np.sum(img_bw)/zoomfactor**2, min_size/zoomfactor**2)
    
    return DataTree(image=img, adjusted=image, binarized=img_bw)

def argvaluechanges(data):
    indices = (np.where(data[:-1] != data[1:])[0]).astype(int)
    return indices

def samplemeasurement(scale, img_bw, zoomfactor, dbg=False):
    
    hori_indices = list(argvaluechanges(np.sum(img_bw, 0) > 0))
    vert_indices = list(argvaluechanges(np.sum(img_bw, 1) > 0))
    debug(hori_indices, vert_indices)
    
    hori_sums = (np.sum(img_bw, 0) > 0).astype('uint8')
    vert_sums = (np.sum(img_bw, 1) > 0).astype('uint8')
    
    dbg and debug( hori_sums )
    dbg and debug( vert_sums )

    # ===========================================================
    # = Handle case where sample runs to an edge (vert or hori) =
    # ===========================================================
    def singleindex(arr_sums, indicies, maxdim):
        sum_idx = np.where(arr_sums > 0)[0]
        debug(sum_idx[-1], sum_idx[0])
        if sum_idx[-1] + 1 == img_bw.shape[0]:
            indicies.append(sum_idx[-1])
        elif sum_idx[0] == 0:
            indicies.append(sum_idx[0])
        
    if len(vert_indices) == 1:
        singleindex(vert_sums, vert_indices, maxdim=img_bw.shape[0])
    if len(hori_indices) == 1:
        singleindex(hori_sums, hori_indices, maxdim=img_bw.shape[1])
        
    # ====================
    # = Check for errors =
    # ====================
    if len(vert_indices) > 2 or len(hori_indices) > 2:
        raise ValueError("IndexingError:TooMany", "Can only handle one object! Check min_size settings")
        
    elif len(vert_indices) == 0 or len(hori_indices) == 0:
        print("Image sums:")
        debug( hori_sums )
        debug( vert_sums )
        raise ValueError("IndexingError:NoObjects", "No objects found! Check image settings", )
    
    # ======================================
    # = Find Sample Shape and Measurements =
    # ======================================
    top, bottom = vert_indices[0], vert_indices[-1]
    left, right = hori_indices[0], hori_indices[-1]
    vsize, hsize = bottom-top, right-left
    rawboundingbox = DataTree(top=top, left=left, right=right, bottom=bottom, units="px")
    boundingbox    = DataTree( { k:v/scale.value for k,v in rawboundingbox.items() if k != "units"} , units="mm")
    
    def calcwidths(arr):
        widths = (np.sum(arr, 1))/scale.value
        return valueUnitsStd(np.mean(widths), stdev=np.std(widths), units="mm")._asdict()
    
    measurements = DataTree()
    measurements.rawboundingbox = rawboundingbox
    measurements.boundingbox = boundingbox
    
    idx_upper = np.s_[top+0*vsize//3:top+1*vsize//3]
    idx_middle = np.s_[top+1*vsize//3:top+2*vsize//3]
    idx_lower = np.s_[top+2*vsize//3:top+3*vsize//3]
    
    debug(idx_upper, idx_middle, idx_lower, )
    measurements["raw","widths"] = calcwidths(img_bw[top:bottom])
    measurements["thirds", "upper"]  = calcwidths(img_bw[idx_upper])
    measurements["thirds", "middle"] = calcwidths(img_bw[idx_middle])
    measurements["thirds", "lower"]  = calcwidths(img_bw[idx_lower])
    
    measurements["thirds", "middleValues"] = (np.sum(img_bw[idx_middle], 1)/scale.value)[::scale.value//zoomfactor]
    
    return measurements

def crop(img, xd, yd, **kws):
    xd_ = np.s_[xd[0]:xd[1]]
    yd_ = np.s_[yd[0]:yd[1]]
    crop_img = img[yd_, xd_]
    return crop_img

def process_image(testconf, imagepath, scaling, cropping, minsamplesize, zoomfactor, equalize_adapthist, imageconf, state, args):
    
    
    processingconfs = DataTree(
                max_width=2.0, # e.g. mm (converted to pixels during processing)
                gamma=1.0, 
                gain= 1.0, 
                img_otsu=0.14,  
                remove_small=True, 
                remove_small_pre=True,
                min_size=minsamplesize.x*minsamplesize.z*scaling.value**2,
                auto_otsu=True,
                equalize_adapthist=equalize_adapthist,
                erode_pixels=1, # 1 pixel of erosion at 2*zoom yields good avg of extra pixel gained during binarization/measurement
                )
    
    processingconfs.update( { k:v for k,v in state["image_measurement","parameters"].items() if k in processingconfs } )
    
    # The cropped image will be "zoomed" so adjust the scaling factor appropriately
    args["dbg","image_measurement"] and debug(zoomfactor)
    
    if testconf['options','processing']:
        processingconfs.update(testconf['options','processing'])
    
    def getimagepath(stage):
        return state.processed / "{name}.{stage}.png".format(name=imageconf["name"], stage=stage)
    
    croppedimage = getimagepath(stage="cropped")
    args["dbg","image_measurement"] and debug(croppedimage)
    
    if not imagepath or not imagepath.exists():
        raise ValueError("Image file not found: "+str(croppedimage), imageconf)
    
    if not croppedimage.exists() or args["force", "imagecaching"]:
        print("Cropping and caching image")
        img = loadimage(imagepath=imagepath)
        debug(img.shape)
        imgout = crop(img, **cropping)
        imgout = scipy.ndimage.zoom(imgout, (zoomfactor, zoomfactor, 1), order=3)
        debug(imgout.shape)
        saveimage(imgout, croppedimage)
    
    image = loadimage(croppedimage)
    
    # =================
    # = Process Image =
    # =================
    
    args_processimg = DataTree(img=image, scale=scaling, zoomfactor=zoomfactor, 
                                dbg=args["dbg","image_measurement"], **processingconfs)
    try:
        processedimages = processimg(**args_processimg)
    except ValueError as err:
        # = Handle case where equalize_adapthist fails (this could be improved via a two stage algo) =
        if processingconfs["equalize_adapthist"] == True:           
            processedimages = processimg(**args_processimg.set(equalize_adapthist=False))
            logging.warning("Binarized image below minimum size! Turned off skimage.exposure.equalize_adapthist")
        
    
    saveimage(processedimages.adjusted, getimagepath("adjusted"))
    saveimage(processedimages.binarized, getimagepath("binarized"))
    
    return processedimages
        
def process_imageconf(testconf, imageconf, state, args):
    
    # Image Measurement Scaling
    zoomfactor = state["image_measurement","parameters"].get("zoomfactor", 2)
    minsamplesize = state["image_measurement","parameters"]["minsamplesize"]
    scaling = getproperty(state["image_measurement"]["scales"], action=True, env=state)
    scaling = scaling.set(value=scaling.value*zoomfactor)
    
    # Image Cropping
    cropping = state.image_measurement["crops"]
    while isinstance(cropping, collections.Mapping) and '_lookup_' in cropping:
        cropping = getproperty(cropping, action=True, env=state)
        args["dbg","image_measurement"] and debug(cropping)
        
    # === Process Image === 
    processedFolder = testconf.folder.images / 'processed'
    
    if not processedFolder.exists():
        os.mkdir(str(processedFolder))
        
    if not imageconf["name"] in testconf.folder.keys():
        raise ValueError("Missing file in projdesc.json configuration. ", imageconf)
    
    imagepath = builtin_action_resolve(testconf.folder[imageconf["name"]], env=state)

    print("Processing Image Measurements from: ", imagepath)
    imageprocessstate = state.set(imagepath=imagepath, processed=processedFolder)
    
    args_process_img = DataTree(testconf=testconf, imageconf=imageconf, imagepath=imagepath, 
                                    scaling=scaling, cropping=cropping, zoomfactor=zoomfactor, 
                                    equalize_adapthist=True,
                                    minsamplesize=minsamplesize, # rough sample size est
                                    state=imageprocessstate, args=args)
    
    processedimages = process_image(**args_process_img)
    args_samplemeasurement = DataTree(scale=scaling, img_bw=processedimages.binarized, zoomfactor=zoomfactor, 
                                        dbg=args["dbg","image_measurement"])

    try:
        measurements = samplemeasurement(**args_samplemeasurement)
    except ValueError as err:
        if err.args[0] == "IndexingError:TooMany":
            processedimages = process_image(**args_process_img.set(equalize_adapthist=False))
            measurements = samplemeasurement(**args_samplemeasurement)
            logging.warn("Too many objects found, turning. Turned off skimage.exposure.equalize_adapthist")
    
    measurements["parameters", "scale"] = scaling  
    measurements["parameters", "zoomfactor"] = valueUnits(100*zoomfactor, units='%')._asdict()
    
    args["dbg","image_measurement"] and debug(measurements)
    
    jsonpath, allmeasurements = testconf.folder.save_calculated_json(
        test=state.args.testconf, 
        name="measurements",
        field="images",
        data={ imageconf["name"]: measurements },
        )

    return allmeasurements

def process_test(testconf, state, args):
    
    image_measurement = state["image_measurement"]
    
    args["dbg","image_measurement"] and debug(image_measurement)
    
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
            args["dbg","image_measurement"] and debug(name, calcexpr)
            result = executeexpr(calcexpr, results=results, calc=env, **allmeasurements["measurements"])
            args["dbg","image_measurement"] and debug(result)
            results[calcname, name] = result

    testconf.folder.save_calculated_json(data=results, test=state.args.testconf, name="measurements", field="images")

