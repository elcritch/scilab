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

base1 = "/Users/jaremycreechley/cloud/bsu/02_Lab/01_Projects/01_Active/Meniscus (Failure Project)/07_Experiments/fatigue failure (cycles, expr1)/05_Code/01_Libraries"
base2 = "/Users/elcritch/Cloud/gdrive/Research/Meniscus (Failure Project)/07_Experiments/fatigue failure (cycles, expr1)/05_Code/01_Libraries"

sys.path.insert(0,base2)
sys.path.insert(0,base1)

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
    

def find_index(time, times):
    for i, tau in enumerate(times):
        if time <= tau:
            return i


def image_tables(testinfo, imgs, out):
    
    # Images Table
    table2 = ImageTable()
    
    [ table2.add_row([img.name, ImgPath(img), ]) for img in images ] 

    # print( mdHeader(2,test.info.name), file=out, file=report)
    
    print( table2.generateTable(headers=['File','Image'], tablefmt='pipe').format(), file=out)


from scilab.tools.instroncsv import csvread

def print_csv_data(testinfo, testfolder, details, report):
    
    fatigue_data = """
        Short Name,set,location,sample,Test Name,Level,Area,DM3,Pred UTS,Orient,Cycles (1st Quartile),Cycles (4th Quartile),UTS Load,Max Strain
        1002-1LG-1001,1002,1LG,1001,,90%,0.788,120.33,12.635,,29,39,,
        1002-1LG-701,1002,1LG,701,,60%,1.13,160.73,17.66,LG,972,975,,
        1002-1LG-702,1002,1LG,702,,70%,1.466,141.22,15.716,,,,25,
        1002-1LG-902,1002,1LG,902,,80%,0.931,136.98,15.293,LG,104,105,,
        1002-1TR-601,1002,1TR,601,,60%,0.16894,5.563,0.5,,,,2.1,
        1002-1TR-602,1002,1TR,602,,70%,1.1296,12.035,5.4,,11,12,,
        1002-1TR-603,1002,1TR,603,,70%,1.02,5.433,1.056,,,,1.7,
        1002-1TR-801,1002,1TR,801,,80%,0.7912,5.319,1.016,,3790,3791,,
        1006-1TR-501,1006,1TR,501,,90%,0.713,4.942,0.884,,,,,
        1006-1TR-502,1006,1TR,502,,80%,0.555,4.72,0.644,,1,21,,
        1006-1TR-701,1006,1TR,701,,70%,0.786,8.083,1.39,,1597,1598,,
        1006-1TR-702,1006,1TR,702,,60%,0.701,10.939,2.988,,6620,6630,,
        1009-1LG-1002,1009,1LG,1002,jan10(gf10.9-llm)-wa-lg-l10-x2,60%,1.02,133.97,14.994,LG,,,14,
        1009-1LG-1003,1009,1LG,1003,jan10(gf10.9-llm)-wa-lg-l10-x3,70%,0.72,156.2,17.208,LG,98,99,,
        1009-1LG-1201,1009,1LG,1201,jan10(gf10.9-llm)-wa-lg-l12-x1,80%,1.2,192.6,20.83,LG,,,38,
        1009-1LG-1202,1009,1LG,1202,jan10(gf10.9-llm)-wa-lg-l12-x2,90%,1.36,118.05,13.407,LG,184,185,,
        1009-1LG-1203,1009,1LG,1203,jan10(gf10.9-llm)-wa-lg-l12-x3,80%,1.1,97.07,11.317,LG,559,560,,
        1009-1TR-1101,1009,1TR,1101,,70%,0.79,9.742,2.568,,,,5,
        1009-1TR-1102,1009,1TR,1102,,60%,1.02,9.632,2.529,,,,6.7,
        1009-1TR-902,1009,1TR,902,,90%,0.87,7.029,1.615,,,,3.4,
        1009-1TR-903,1009,1TR,903,,90%,0.88,14.487,4.233,,1,1,,
        1104-1LG-501,1104,1LG,501,jan11(gf11.4-llm)-wa-lg-l5-x1,90%,1.1,113.96,12.99,LG,1,17,,
        1104-1LG-502,1104,1LG,502,jan11(gf11.4-llm)-wa-lg-l5-x2,80%,1.56,64.166,8.03,LG,102,126,,
        1104-1LG-701,1104,1LG,701,jan11(gf11.4-llm)-wa-lg-l7-x1,70%,1.26,207.92,22.361,LG,,,12,
        1104-1LG-702,1104,1LG,702,jan11(gf11.4-llm)-wa-lg-l7-x2,60%,1.26,113.76,12.98,LG,,,12,
        1105-1LG-601,1105,1LG,601,jan11(gf11.5-llm)-wa-lg-l6-x1,60%,0.88,250.89,26.642,LG,,,24,
        1105-1LG-602,1105,1LG,602,jan11(gf11.5-llm)-wa-lg-l6-x2,70%,0.93,171.9,18.772,LG,198,199,,
        1105-1LG-801,1105,1LG,801,jan11(gf11.5-llm)-wa-lg-l8-x1,80%,1.23,19.789,19.789,LG,751,752,,
        1105-1LG-802,1105,1LG,802,jan11(gf11.5-llm)-wa-lg-l8-x2,90%,1.81,143.35,15.928,LG,25,26,,
        1105-1TR-501,1105,1TR,501,,90%,0.52,8.92,2.279,,104,105,,
        1105-1TR-502,1105,1TR,502,,80%,0.38,7.899,1.921,,7,8,,
        1105-1TR-701,1105,1TR,701,,70%,0.67,11.912,3.329,,16,18,,
        1105-1TR-702,1105,1TR,702,,60%,0.629,8.977,2.3,,143,145,,
        """
    
    def values(v):
        try:
            return int(v)
        except:
            try:
                return float(v)
            except:
                return v

    fatigue_header, *fatigue_rows = [ l.strip().split(',') for l in fatigue_data.strip().split('\n') ]
    # debug(fatigue_header)
    
    fatigue_dicts = [ { k:values(i) for k,i in zip(fatigue_header, r) } for r in fatigue_rows ]
    fatigue_dicts = DataTree(**{ r['Short Name']:r for r in fatigue_dicts })
    
    # debug(fatigue_dicts)
    
    
    
    print(mdHeader(3, "CSV Data" ), file=report)
    
    # KeyError: "Key 'elapsedStep' not found in: step, loadLinearLoad1Maximum, displacementLinearDigitalPositionMinimum, rotationRotaryRotationMinimum, torqueRotaryTorqueMinimum, rotationRotaryRotationMaximum, torqueRotaryTorqueMaximum, indices, positionLinearPositionMaximum, rotaryDisplacementRotaryDigitalRotationMaximum, rotaryDisplacementRotaryDigitalRotationMinimum, loadLinearLoadMaximum, loadLinearLoad1Minimum, elapsedCycles, pc|frequency, _matrix, _InstronMatrixData__slices, displacementLinearDigitalPositionMaximum, totalCycles, loadLinearLoadMinimum, positionLinearPositionMinimum, pc|cycleStartTime"

    if testinfo.orientation == 'lg':
        trendsfolder = testfolder.raws.cycles_lg_csv
        loads = ['loadLinearLoadMaximum','loadLinearLoadMinimum']        
        loadsTracking = 'loadLinearLoad'        
    elif testinfo.orientation == 'tr':
        trendsfolder = testfolder.raws.cycles_tr_csv
        loads = ['loadLinearLoad1Maximum','loadLinearLoad1Maximum']
        loadsTracking = 'loadLinearLoad1'
    
    debug(testinfo.short(), trendsfolder)
    
    if not trendsfolder.trends or not trendsfolder.trends.exists():
        print("Error: couldn't find trend files! (%s)"%(str(testinfo),), file=report)
        return 
        
    trends = csvread(str(trendsfolder.trends))
    
    indicies = trends._getslices('step')
    debug(indicies)
    
    sl_fatigue = indicies[5]
    # sl_uts = indicies[7]
    
    def fmt(name, N=-25, O=-1):
        if hasattr(name, '__call__'):
            return name(trends, N, O)[1]
        return trends[name].array[N:O]
        
    columns = [
        'elapsedCycles', 
        'step', 
        'displacementLinearDigitalPositionMinimum', 
        'displacementLinearDigitalPositionMaximum',
        lambda x,N,O: ('Min Strain', x['displacementLinearDigitalPositionMinimum'].array[N:O]/details.gauge.value),
        lambda x,N,O: ('Max Strain', x['displacementLinearDigitalPositionMaximum'].array[N:O]/details.gauge.value),
        ]+loads
        
    def short(name, N=-1, O=-1):
        if hasattr(name, '__call__'):
            return name(trends, N, O)[0]
        return name.replace('Linear', '').replace('displacement', 'disp').replace('DigitalPosition','')
    
    
    fatigue_dict = fatigue_dicts.get(testinfo.short(),None) 
    quartile1 = 'Cycles (1st Quartile)'
    quartile4 = 'Cycles (4th Quartile)'
    print(mdBlock("Fatigue Data:"+str(fatigue_dict)), file=report)

    
    if fatigue_dict and fatigue_dict[quartile4]:
        
        startEndCycleIdx = find_index(fatigue_dict[quartile1], trends['elapsedCycles'].array[sl_fatigue])
        lastCycleIdx = find_index(fatigue_dict[quartile4], trends['elapsedCycles'].array[sl_fatigue])
        N, O = startEndCycleIdx-1, lastCycleIdx
        
        if not lastCycleIdx:
            debug(trends['elapsedCycles'].array[sl_fatigue])
            
        debug(startEndCycleIdx, lastCycleIdx, N, O)
        
        lastCycleMaxPosition = (trends['displacementLinearDigitalPositionMaximum'].array[sl_fatigue])[lastCycleIdx]
        
        debug(lastCycleMaxPosition, fatigue_dict)
        
        print(mdBlock("**Fatigue Cycle**: {'id': '%s', 'loc': '%s', 'max disp': %.3f, 'max strain':%.3f, 'lastCycle': %d, 'timeLast': %.3f} "%(
                    fatigue_dict['Short Name'],
                    fatigue_dict['location'],
                    lastCycleMaxPosition,
                    lastCycleMaxPosition/details.gauge.value,
                    fatigue_dict[quartile4],
                    trends['pc|cycleStartTime'].array[sl_fatigue][lastCycleIdx]
                    ),
                ), file=report)
    else:
        N, O = -25, -1
    
    if fatigue_dict and fatigue_dict['UTS Load']:
        
        tracking = csvread(str(trendsfolder.tracking))
        
        track_indicies = trends._getslices('step')
        sl_uts = track_indicies[7]
        debug(track_indicies, sl_uts)
            
        maxload = data_find_max(tracking[loadsTracking].array[sl_uts])
        debug(maxload)
        
        maxes = DataTree()
        maxes.load = maxload.value
        maxes.stress = maxes.load / details.measurements.area.value

        maxes.displacement = tracking.displacement.array[sl_uts][maxload.idx]
        maxes.strain = maxes.displacement / details.gauge.value

        debug(maxes)
                
        print(mdBlock("**UTS Load**: %s: %s, %s, %.3f, %.3f, %.3f, %.3f, , %.3f, %.3f, %d, %.3f "%(
                    'Name, Orient, UTS Load (manual), UTS Stress (manual), disp, strain, load, stress, idx, time',
                    fatigue_dict['Short Name'],
                    fatigue_dict['location'],
                    fatigue_dict['UTS Load'],
                    fatigue_dict['UTS Load']/details.gauge.value,
                    maxes.displacement,
                    maxes.strain,
                    maxes.load,
                    maxes.stress,
                    maxload.idx,
                    tracking.totalTime.array[sl_uts][maxload.idx],
                    )), file=report)    
    
    tabledata = OrderedDict([(short(col), fmt(col, N, O)) for col in columns ])    
    print(tabulate(tabledata, headers="keys", numalign="right", floatfmt=".2f"), file=report)
    
    
    print(mdBlock("Steps: "), set(trends['step'].array.tolist()), file=report)
    
    
def print_datasheet(testinfo, testfolder, report):
    
    print(mdHeader(3, "DataSheet Info" ), file=report)
    details = Json.load_json(testfolder.json, json_url=testinfo.name+'.calculated.json') 

    # debug(details)
    fdetails = flatten(details, sep='.')
    # debug(fdetails)


    name = OrderedDict()
    # name["Short Name"] = "Short Name"
    # name["info.name"] = "info.name"
    # name["linear_modulus.value"] = "Toe Linear Modulus"
    # name["linear_modulus.slope_strain"] = "TLM Strain Slope"
    # name["linear_modulus.slope_stress"] = "TLM Stress Slope"
    # name["calculations.maxes.displacement.value"] = "displacement.value"
    # name["calculations.maxes.load.value"] = "load.value"
    # name["calculations.maxes.strain.value"] = "strain.value"
    # name["calculations.maxes.stress.value"] = "stress.value"
    name["measurements.area.units"] = "area.units"
    name["measurements.area.value"] = "area.value"
    name["measurements.depth.stdev"] = "depth.stdev"
    name["measurements.depth.value"] = "depth.value"
    name["measurements.width.stdev"] = "width.stdev"
    name["measurements.width.value"] = "width.value"
    name["gauge.base"] = "gauge.base"
    name["gauge.preloaded"] = "gauge.preloaded"
    name["gauge.value"] = "gauge.value"
    # name["info.sample"] = "info.sample"
    # name["info.layer"] = "info.layer"
    # name["info.orientation"] = "info.orientation"
    # name["info.wedge"] = "info.wedge"
    # name["info.side"] = "info.side"
    # name["info.set"] = "info.set"
    # name["info.date"] = "info.date"
    # name["info.run"] = "info.run"
    # name["name"] = "File Name"

    for k,v in name.items():
        v = v.replace('.value','').split('.')
        name[k] = ' '.join( [ s[0].upper()+s[1:] for s in v ] )

    

    # print(*name.values(),sep='\n')
    # make table
    def values(v):
        try:
            if type(v) == float:
                return "%.3f"%v
            elif type(v) == int:
                return "%d"%v
        except:
            return v
        
    data =  [ (k, values(fdetails.get(k,None))) for k in name ]

    # debug(data)
    
    print(tabulate(data, headers=['Name', 'Value'], numalign="right", floatfmt=".2f"), file=report)

    return details


def process_test(testinfo, testfolder, report):

    # debug(testinfo)

    print(mdHeader(2, "Test: " + str(testinfo) ), file=report)

    details = print_datasheet(testinfo, testfolder, report)
    
    print_csv_data(testinfo, testfolder, details, report)
    
    
    testImages = findFilesIn(testfolder.images, kind='JPG')
    # testImages = testfolder.images.glob('*.png')
    testGraphs = findFilesIn(testfolder.graphs, kind='png')
    
    import urllib.parse 
    
    print(mdHeader(3, "Graphs" ), file=report)
    
    stepLastGraph = next((g for g in testGraphs if 'step last' in g.name), None)
    reportdir = Path(report.name).parent
    debug(stepLastGraph, reportdir)
    
    if stepLastGraph:
        stepLastGraph = '..' / stepLastGraph.absolute().relative_to(testfolder.project_dir) 
        print( '![%s](%s)'%(stepLastGraph.name, urllib.parse.quote(str(stepLastGraph))), file=report)
    
    # debug(testfolder.images, testImages, testGraphs)
    
    # return handler(trackingtest, testinfo, data_tracking=data_tracking, details=None, args=args)



def main():
    
    
    fs = FileStructure('fatigue failure (cycles, expr1)', 'cycles-expr2')
    # Test test images for now
    test_dir = fs.test_parent.resolve()
    
    
    testitemsd = fs.testitemsd()

    with open(str(fs.results_dir/'Test Measurement Details.v2.md'),'w') as report:
        

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