#!/usr/bin/env python3
# coding: utf-8

import csv
import sys, os

from pylab import *
from scipy.stats import exponweib, weibull_max, weibull_min
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter, MaxNLocator
import glob, logging

from tabulate import tabulate
from collections import OrderedDict

base = "/Users/elcritch/Cloud/gdrive/Research/Meniscus (Failure Project)/07_Experiments/fatigue failure (cycles, expr1)/05_Code/01_Libraries"
sys.path.insert(0,base)

from scilab.tools.project import *
from scilab.tools.graphing import *
from scilab.tools.instroncsv import *

import scilab.tools.project as Project
import scilab.tools.excel as Excel
import scilab.tools.graphing as Graphing
import scilab.tools.scriptrunner as ScriptRunner
import scilab.tools.json as Json

from scilab.tools.tables import mdBlock, mdHeader, ImageTable, MarkdownTable

from scilab.expers.mechanical.fatigue.cycles import FileStructure
from scilab.expers.mechanical.fatigue.cycles import TestInfo as TestInfo
from scilab.expers.mechanical.fatigue.helpers import *
import scilab.tools.json as Json

from scilab.expers.mechanical.fatigue.cycles import TestInfo

PlotData = namedtuple('PlotData', 'array label units max')

def info_table(testinfo, out):
    
    infoTable = MarkdownTable()

    row = ['**{}**'.format(testinfo.short()) ]
    row += testinfo[1:] 
    infoTable.add_row( row )

    print( infoTable.generateTable(headers=TestInfo._fields, tablefmt='pipe').format(), file=out)
    

def image_tables(testinfo, imgs, out):
    
    # Images Table
    table2 = ImageTable()
    
    [ table2.add_row([img.name, ImgPath(img), ]) for img in images ] 

    # print( mdHeader(2,test.info.name), file=out)
    
    print( table2.generateTable(headers=['File','Image'], tablefmt='pipe').format(), file=out)


from scilab.tools.instroncsv import csvread

def print_csv_data(testinfo, testfolder, report):
    
    print(mdHeader(3, "CSV Data" ), file=report)
    
    # KeyError: "Key 'elapsedStep' not found in: step, loadLinearLoad1Maximum, displacementLinearDigitalPositionMinimum, rotationRotaryRotationMinimum, torqueRotaryTorqueMinimum, rotationRotaryRotationMaximum, torqueRotaryTorqueMaximum, indices, positionLinearPositionMaximum, rotaryDisplacementRotaryDigitalRotationMaximum, rotaryDisplacementRotaryDigitalRotationMinimum, loadLinearLoadMaximum, loadLinearLoad1Minimum, elapsedCycles, pc|frequency, _matrix, _InstronMatrixData__slices, displacementLinearDigitalPositionMaximum, totalCycles, loadLinearLoadMinimum, positionLinearPositionMinimum, pc|cycleStartTime"

    if testinfo.orientation == 'lg':
        trendsfolder = testfolder.raws.cycles_lg_csv.trends 
        loads = ['loadLinearLoadMaximum','loadLinearLoadMinimum']        
    elif testinfo.orientation == 'tr':
        trendsfolder = testfolder.raws.cycles_tr_csv.trends 
        loads = ['loadLinearLoad1Maximum','loadLinearLoad1Maximum']
    
    debug(testinfo.short(), trendsfolder)
    
    if not trendsfolder or not trendsfolder.exists():
        print("Error: couldn't find trend files! (%s)"%(str(testinfo),))
        return 
        
    trends = csvread(str(trendsfolder))
    
    def fmt(name):
        return trends[name].array[-15:]
        
    columns = [
        'elapsedCycles', 
        'step', 
        'displacementLinearDigitalPositionMinimum', 
        'displacementLinearDigitalPositionMaximum',
        ]+loads
        
    def short(name):
        return name.replace('Linear', '').replace('displacement', 'disp').replace('DigitalPosition','')
        
    print(tabulate(OrderedDict({ short(col): fmt(col) for col in columns }), headers="keys", numalign="right", floatfmt=".2f"))
    
    print(mdBlock("Steps: "), set(trends['step'].array.tolist()))
    
def process_test(testinfo, testfolder, report):

    # debug(testinfo)

    print(mdHeader(2, "Test: " + str(testinfo) ))

    print_csv_data(testinfo, testfolder, report)
    
    
    testImages = findFilesIn(testfolder.images, kind='JPG')
    # testImages = testfolder.images.glob('*.png')
    testGraphs = findFilesIn(testfolder.images, kind='png')
    
    # debug(testfolder.images, testImages, testGraphs)
    
    # return handler(trackingtest, testinfo, data_tracking=data_tracking, details=None, args=args)



def main():
    
    
    fs = FileStructure('fatigue failure (cycles, expr1)', 'cycles-expr2')
    # Test test images for now
    test_dir = fs.test_parent.resolve()
    
    
    testitemsd = fs.testitemsd()

    with open(str(fs.test_parent/'Test Measurement Details.v3.md'),'w') as report:
        

        for testinfo, testfile  in testitemsd.items():
        
            # debug(type(testinfo), testinfo, testfile)
        
            try:
                ti = TestInfo(name=testfile.name)
            except:
                ti = None
        
            if not ti:
                continue
        
            testfolder = fs.testfolder(testinfo=ti, ensure_folders_exists=False)

            process_test(ti, testfolder, report)
    
if __name__ == '__main__':
    main()