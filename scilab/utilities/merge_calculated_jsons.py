#!/usr/bin/env python3


import shutil, re, sys, os, itertools, argparse, json, collections
from pathlib import Path
import jsonmerge

from collections import OrderedDict

import openpyxl
from openpyxl import load_workbook

# import scilab.tools.scriptrunner as ScriptRunner
# from scilab.tools.scriptrunner import RESEARCH, RAWDATA, debug

import logging

from scilab.tools.excel import *
from scilab.tools.project import *

import scilab.tools.jsonutils as Json
# from scilab.expers.mechanical.fatigue.uts import UtsTestInfo
from scilab.tools.tables import mdBlock, mdHeader, ImageTable, MarkdownTable
    
## Main

def handleForNow():
    """ This is a week garauntee of uniqueness, but it should be good enough for this task. """
    import datetime
    today = datetime.datetime.today()
    return "{year}-{month}-{day}_{hour}:{minute}:{second}".format(**{k:getattr(today,k) for k in dir(today)})
    
def doSavePrevous(json_current, json_updated):
    """ take prevous from current, and add current to it and set it on the new updated json. """
    previous = json_current.pop('previous') if 'previous' in json_current else OrderedDict()

    previous[handleForNow()] = json_current
    json_updated['previous'] = previous

def graphs2_handler(testinfo, testfolder, testdata, args, savePrevious=True):

    return handler(testinfo=testinfo, testfolder=testfolder, args=args, savePrevious=savePrevious)

def handler(testinfo, testfolder, args, savePrevious=True):
    
    testcalc = (testfolder.json / (testinfo.name + '.calculated.json'))
    
    subcalcs = testfolder.jsoncalc.glob(testinfo.name+'.*.calculated.json')

    def getJson(subcalc):
        debug(subcalc.name)
        return Json.load_json(subcalc.parent.as_posix(), json_url=subcalc.name)
        
    subjsons = [ getJson(subcalc) for subcalc in subcalcs ]

    json_current = getJson(testcalc)
    
    # json_updated = jsonmerge.merge(json_current, {})
    json_updated = {}
    for js in subjsons:
        json_updated = jsonmerge.merge(json_updated, js)
        
    debug(json_updated)
    
    if savePrevious:
        Json.update_json(testcalc.parent.as_posix(), {handleForNow(): json_updated}, 
                json_url=testcalc.with_suffix('.previous.json').name, default={}, dbg=False)
        
    
    print("Updating: "+testinfo.name+" "+str([str(s) for s in json_updated.keys()]))
    Json.write_json(testcalc.parent.as_posix(), json_updated, 
            json_url=testcalc.name, dbg=False)
    
    
    return json_updated

if __name__ == '__main__':

    # Json.write_json = lambda *a, **x: print("Write Json:", a[0], len(x))
    # Json.update_json = lambda *a, **x: print("Update Json:", a[0], len(x))

    parser = ScriptRunner.parser
    
    parser.add_argument("-n", "--name", default="data", type=str)

    ## Test

    projectspath = Path(RESEARCH) / '07_Experiments'
    projectpath = projectspath/'fatigue failure (UTS, exper1)'
    
    debug(projectpath.resolve())
    
    experUtsCsv = projectpath / '04 (uts) uts-test' 
    experUtsPreconds = projectpath / '02 (uts) preconditions' 
    experData = projectpath / 'test-data'/'uts (expr-1)'
    experExcel = experData / '01 Excel' 
    experJson = experData / '00 JSON'
    experReport = experData / '02 Reports'
    experReportGraphs = experData / '03 Graphs'
    experJsonCalc = experJson / 'calculated'
    
    files = experExcel.glob('*.xlsx')

    test_args = []
    # test_args = ["--glob", fileglob]
    # test_args += ['-1'] # only first
    
    args = parser.parse_args( test_args ) 
    [ setattr(args,e,v) for e,v in locals().items() if e.startswith('exper' )] 
    
    if 'args' not in locals(): 
        args = parser.parse_args() 
    
    
    
    # files = experExcel.glob('*.xlsx')
    # debug(experExcel, list(files))
    mergedjs = collections.OrderedDict()
    
    for test in list(files)[:]:
    
        debug(test.name)

        testinfo = UtsTestInfo(name=test.stem)
        
        testjs = handler(testfile=test, testinfo=testinfo, args=args)
    
        mergedjs[testinfo.name] = testjs
        
    Json.write_json(experJson.as_posix(), mergedjs, 
                json_url="all.calculated.json", dbg=False)
        
    
    
