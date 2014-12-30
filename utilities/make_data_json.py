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
    
    data['measurements'] = measurements
    
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

def parse_data_from_worksheet(file_name, file_path, file_parent, args):

    try:
        abs_file_path = os.path.realpath(file_path)
        wb = load_workbook(abs_file_path, data_only=True)
    except (Exception) as err:
        logging.warn("Cannot open file:\n\t"+file_path+"\n\t vs \n\t"+abs_file_path)
        raise err
        
    ## Process Excel Sheets
    ws = wb.worksheets[0]
    data = parse_fatigue_data_sheet_v1(ws)    
    
    ## Handle Names    
    data['name'] = os.path.splitext(file_name)[0]
    debug(data['name'])
    
    ## Get Test ID 
    match = re.match(r'(.+)\((.+)-(.+)\)[-]*(.+?)-(.+?)-(.+?)-(\w+)(?:-(.+))*', data['name'])
        
    testDate, sample, section, orientation, zone, layer, specimen = match.groups()[:7]
    nums = lambda s: ''.join( c for c in s if c.isdigit() )
    
    data['id'] = '.'.join(map(nums,sample.split('.')))+'.'+nums(zone+layer+specimen)
    
    debug(data['id'])
    
    Json.write_json(file_parent, data, json_url=data['name']+'.json', dbg=True)
    
    return
    

def handler(file, args):
    
    print("Excel notebooks:", file.name)
    print()
    
    parse_data_from_worksheet(
        file_name=str(test.name), 
        file_path=str(test.resolve()), 
        file_parent=str(test.parent), 
        args=args)
    
    return

if __name__ == '__main__':

    parser = ScriptRunner.parser
    
    parser.add_argument("-n", "--name", default="data", type=str)

    ## Test

    projectname = 'NTM-MF/fatigue-failure-expr1/'
    projectpath = Path(RAWDATA) / projectname
    
    files = projectpath.glob('test-data/uts/nov*.xlsx')

    test_args = []
    # test_args = ["--glob", fileglob]
    # test_args += ['-1'] # only first
    
    args = parser.parse_args( test_args )    
    # args = parser.parse_args()
    
    if 'args' not in locals():
        args = parser.parse_args()
    
    # ScriptRunner.process_files_with(args=args, handler=handler)
    
    for test in list(files)[:]:
        
        debug(test)
        
        handler(file=test, args=args)
    
    
    
