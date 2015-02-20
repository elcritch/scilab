#!/usr/bin/env python3

# coding: utf-8

import os, sys, functools, itertools, collections, re, logging
from pathlib import *
from tabulate import *

import matplotlib.pyplot as plt

base1 = "/Users/jaremycreechley/cloud/bsu/02_Lab/01_Projects/01_Active/Meniscus (Failure Project)/07_Experiments/fatigue failure (cycles, expr1)/05_Code/01_Libraries"
base2 = "/Users/elcritch/Cloud/gdrive/Research/Meniscus (Failure Project)/07_Experiments/fatigue failure (cycles, expr1)/05_Code/01_Libraries"
base3 = '/Users/elcritch/Cloud/gdrive/Research/Meniscus (Failure Project)/07_Experiments/fatigue failure (uts, expr1)/05_Code/01_Libraries'

sys.path.insert(0,base3)

import scilab, scilab.tools.graphing, scilab.tools.json
from scilab.tools.project import *
from scilab.expers.mechanical.fatigue.uts import *

from scilab.tools.tables import mdBlock, mdHeader, ImageTable, MarkdownTable

from scilab.expers.mechanical.fatigue.image_measurements_auto import DIMS, crop, process
import PIL

from fn import _ as __

# from scilab.expers.mechanical.fatigue.cycles import TestInfo, FileStructure
from scilab.expers.mechanical.fatigue.uts import TestInfo, FileStructure

def get_cropped(imgurl:Path, dims=DataTree(xr=(2000,3000), yr=(1000,2000))):
    imgpng = imgurl.with_suffix('.png')
    if imgpng.exists():
        return imgpng
    else:
        img = PIL.Image.open(str(imgurl))
        imgcrop = img.crop((dims.xr[0], dims.yr[0], dims.xr[1], dims.yr[1]))
        imgcrop.save(str(imgpng))
        return imgpng

def processSpecimenImages(testinfo, testfolder, testimages):

    pd = testfolder.images / 'processed'
    if not pd.exists(): pd.mkdir()

    print(mdHeader(1, "Test {}: {}".format(testinfo.name, testinfo.short()) ) )

    orient = testinfo.orientation
    locations=None

# processedDir, testpaths, imgPath, dims, orientation, aspect,      locations
    front, figname1 = process(pd, testfolder, testimages.front, DIMS, orient, 'front', locations)
#    fail, figname2 = process(pd, test.full.fail, DIMS, orient, 'front', min_size=200)
    side, figname3 = process(pd, testfolder, testimages.side, DIMS, orient, 'side', locations)

    measures = DataTree(front=front,side=side)

    for k,measure in measures.items():
        print("## Processing:", k)
        if not measure: continue
#         print("Measurements:\n",flatten(measure.mm.summaries,sep='.'))

    scilab.tools.json.write_json(pd, measures)
    summaries = DataTree(**{ k: v.mm.summaries for k,v in measures.items() if v })
    summaries.units = 'mm'
    summaries.info = testinfo
    summariesName = '{}.measurements.json'.format(testinfo.name)

    debug(summaries)
    scilab.tools.json.write_json(testfolder.jsoncalc, summaries, json_url=summariesName)

    print("Wrote json:", testfolder.jsoncalc)

    return summaries

def first_only(iterable):
    lst = list(iterable)
    if len(lst) != 1:
        raise Exception("Should only return one item, found: "+len(lst))
    return lst[0]

def process_test(testinfo, testfolder):

    front = first_only(testfolder.images.glob('D*.front.JPG'))
    side = first_only(testfolder.images.glob('D*.side.JPG'))

    reducedimgs = DataTree(front=get_cropped(front), side=get_cropped(side))

    return processSpecimenImages(testinfo, testfolder, reducedimgs)


def process_tests(experfiles:FileStructure, testfolders):

    tests = collections.OrderedDict()
    for testfolder in testfolders:

        testinfo = TestInfo(name=testfolder.stem, date='', set='gf10.10', side='llm', wedge='wa', orientation='lg', layer='4', sample='1',run='1')
        tests[testinfo.name] = (testinfo, tests)
    
        process_test(testinfo, experfiles.testfolder(testinfo, ensure_folders_exists=True))
#        process_test(TestInfo(name=str(test)), experfiles.testfolder(testinfo))

def graphs2_handler(testinfo, testfolder, testdata, args, **kwargs):
    
    print("run_image_measure:graphs2_handler:",testinfo.name)
    return process_test(testinfo, testfolder)


def main():

    # experfiles = FileStructure('fatigue failure (cycles, expr1)', 'cycles-expr1')
    experfiles = FileStructure('fatigue failure (uts, expr1)', 'fatigue-test-2')

    debug(experfiles.test_parent)

    testdirs = [ t for t in experfiles.test_parent.glob('*') if t.is_dir() ]

    debug(testdirs)

    testImages = [ (t, list(experfiles.testfolder(t).images.glob('D*.JPG')) )
                    for t in testdirs]

    testImageTimes = [ (t, max(map(lambda _: _.stat().st_mtime, i))) for t,i in testImages if i]
    testsByTime = [ t[0] for t in sorted(testImageTimes, key=__[1]) ]

    debug(testsByTime)
    tests = testsByTime[:1]
    
    print("Processing tests:")

    # process_tests(experfiles, tests)

if __name__ == '__main__':

    main()