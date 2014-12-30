#!/usr/bin/env python3


import shutil, re, sys, os, itertools, argparse, json
from pathlib import Path

import openpyxl
from openpyxl import load_workbook

import scilab.tools.scriptrunner as ScriptRunner
from scilab.tools.scriptrunner import RESEARCH, RAWDATA, debug

import logging

from scilab.tools.excel import *
from scilab.tools.project import DataTree

import scilab.tools.json as Json
from scilab.expers.mechanical.fatigue.uts import UtsTestInfo
    
## Main
    
def parse_fatigue_data_sheet_v1(ws):
    
    rng = rangerForRow(ws)

    data = {}
    data['info'] = DataTree()
    data['info'].update( dictFrom(rng('A1:D1')) )
    
    measurements = DataTree(withProperties='width depth area')
    measurements.width.value = ws['B6'].value
    measurements.depth.value = ws['C6'].value
    measurements.area.value = ws['E6'].value
    
    measurements.width.stdev = ws['B7'].value
    measurements.depth.stdev = ws['C7'].value
    
    measurements.width.units = 'mm'
    measurements.depth.units = 'mm'
    measurements.area.units = 'mm^2'
    
    
    # Process all the values in these rows
    other = DataTree()
    
    ## continue reading the column down 
    end = process_definitions_column(ws, other, 'A',8,30, stop_key='Failure Notes / Test Results', dbg=False)
    ## read next definition column (4 excel columns over)
    process_definitions_column(ws, other, 'D', 7, end, dbg=True)

    # gauge
    data['gauge'] = gauge = DataTree()
    gauge.units = 'mm' # default
    
    if 'gauge' in other:
        gauge.value = other.pop('gauge')
        gauge.base = other.pop('init_position')
    elif 'gauge_base' in other:
        gauge.base = other.pop('gauge_base')
    elif 'base_position' in other:
        gauge.base = other.pop('base_position')
    else:
        logging.warn("Excel file missing gauge_base! Possible keys:\t"+str([ str(k) for k in other.keys() ]) )
    
    
    data['other'] = other
    
    debug(data.keys())
    # data.measurements.area.value = other.pop('area')
    
    notes = {}
    process_definitions_column(ws, notes, 'A', end+1,end+5, stop_key=None, dbg=False)
    data['notes'] = notes
    
    return data
    
def parse_data_from_worksheet(testpath:Path, testinfo:UtsTestInfo, args):

    try:
        wb = load_workbook(testpath.absolute().as_posix(), data_only=True)
    except (Exception) as err:
        logging.warn("Cannot open file:\n\t"+str(testpath)+"\n\t vs \n\t"+testpath.absolute().as_posix())
        raise err
        
    ## Process Excel Sheets
    ws = wb.worksheets[0]
    return parse_fatigue_data_sheet_v1(ws)    


def process_image_measurements(testfile, testinfo, imgdata):
        
    data = {}
    data['info'] = DataTree()
    data['info'].update( testinfo.as_dict() )
    data['info']['set'] = testinfo.name
    
    measurements = DataTree(width=DataTree(), depth=DataTree(), area=DataTree())
    measurements.width.value = imgdata.front.widths.average.mean
    
    if not 'side' in imgdata:
        logging.warn("Could not find side measurement for: "+str(testinfo))
        measurements.depth.value = 1.00
        measurements.depth.stdev = -0.01
    else:
        measurements.depth.value = imgdata.side.widths.average.mean
        measurements.depth.stdev = imgdata.side.widths.average.std
        
    measurements.area.value = float(measurements.width.value)*float(measurements.depth.value)
    
    measurements.width.stdev = imgdata.front.widths.average.std
    
    measurements.width.units = 'mm'
    measurements.depth.units = 'mm'
    measurements.area.units = 'mm^2'
    
    data['measurements'] = measurements
    
    return data

    
def parse_from_image_measurements(testfile, testinfo, args):

    imgMeasureFile = args.experJson / (testinfo.name+'.measurements.json')
    imgMeasureFile = imgMeasureFile.resolve()
    
    imgMeasurements = Json.load_json(imgMeasureFile.parent.as_posix(), json_url=imgMeasureFile.name)
    
    # debug(imgMeasurements)
    
    data = process_image_measurements(testfile, testinfo, imgMeasurements)

    return data
    

def handler(file, args):
    
    print("Excel notebooks:", file.name)

    testinfo = UtsTestInfo(name=file.with_suffix('').name)
    print(str(testinfo))
    
    data = parse_from_image_measurements(
        testfile=file, 
        testinfo=testinfo,
        args=args)
    
    # parse_data_from_worksheet(
    #     testpath=file,
    #     testinfo=testinfo,
    #     args=args)
    
    ## Handle Names    
    data['name'] = testinfo.name
    debug(data['name'])
        
    data['id'] = testinfo.short()
    data['info'] = testinfo.as_dict()
    
    debug(data['id'])
    
    Json.write_json(args.experJson, data, json_url=data['name']+'.calculated.json', dbg=False)
    
    return

if __name__ == '__main__':

    parser = ScriptRunner.parser
    
    parser.add_argument("-n", "--name", default="data", type=str)

    ## Test

    projectname = 'NTM-MF/fatigue-failure-expr1/'
    projectpath = Path(RAWDATA) / projectname
    
    experData = projectpath / 'test-data'/'uts (expr-1)'
    experExcel = experData/'01 Excel' 
    experJson = experData/'00 JSON'
    
    files = experExcel.glob('*.xlsx')

    test_args = []
    # test_args = ["--glob", fileglob]
    # test_args += ['-1'] # only first
    
    args = parser.parse_args( test_args )    
    # args = parser.parse_args()
    
    if 'args' not in locals():
        args = parser.parse_args()
    
    args.projectpath = projectpath
    args.experData = experData
    args.experJson = experJson 
    
    # ScriptRunner.process_files_with(args=args, handler=handler)
    
    for test in list(files)[:]:
        
        debug(test)
        
        handler(file=test, args=args)
    
    
    
