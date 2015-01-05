#!/usr/bin/env python3


import shutil, re, sys, os, itertools, argparse, json, collections
from pathlib import Path
import jsonmerge

from collections import OrderedDict

import openpyxl
from openpyxl import load_workbook

import scilab.tools.scriptrunner as ScriptRunner
from scilab.tools.scriptrunner import RESEARCH, RAWDATA, debug

import logging

from scilab.tools.excel import *
from scilab.tools.project import *

import scilab.tools.json as Json
from scilab.expers.mechanical.fatigue.uts import UtsTestInfo
from scilab.tools.tables import mdBlock, mdHeader, ImageTable, MarkdownTable




if __name__ == '__main__':

    # Json.write_json = lambda *a, **x: print("Write Json:", a[0], len(x))
    # Json.update_json = lambda *a, **x: print("Update Json:", a[0], len(x))

    parser = ScriptRunner.parser
    
    parser.add_argument("-n", "--name", default="data", type=str)

    ## Test

    projectspath = Path(RESEARCH) / '07_Experiments'
    PROJECTPATH = projectspath/'fatigue failure (UTS, exper1)'
    
    debug(PROJECTPATH)
    debug(PROJECTPATH.resolve())
    
    EXPER_PRELOAD_CSV = PROJECTPATH / '01 (uts) preloads' 
    EXPER_PRECONDS_CSV = PROJECTPATH / '02 (uts) preconditions' 
    EXPER_UTS_CSV = PROJECTPATH / '04 (uts) uts-test' 
    
    EXPER_DATA = PROJECTPATH / 'test-data'/'uts (expr-1)'
    EXPER_EXCEL = EXPER_DATA / '01 Excel' 
    EXPER_JSON = EXPER_DATA / '00 JSON'
    EXPER_REPORT = EXPER_DATA / '02 Reports'
    EXPER_REPORTGRAPHS = EXPER_DATA / '03 Graphs'
    EXPER_JSONCALC = EXPER_JSON / 'calculated'
    EXPER_SPECIMENIMAGES = PROJECTPATH / '05 Specimen Images' / '02 Test Images'
    

    test_args = []
    # test_args = ["--glob", fileglob]
    # test_args += ['-1'] # only first
    
    args = parser.parse_args( test_args ) 
    [ setattr(args,e,v) for e,v in locals().items() if e.startswith('exper' )] 
    
    if 'args' not in locals(): 
        args = parser.parse_args() 
    
    
    
    # files = EXPER_EXCEL.glob('*.xlsx')
    # debug(EXPER_EXCEL, list(files))
    mergedjs = collections.OrderedDict()
    
    def test(test):
        try:
            testinfo = UtsTestInfo(name=test.name)
            print(mdHeader(2,str(testinfo)))
            # print(str(testinfo),end=', ')
            print('.',end='')
            errs = testinfo.validate()
            if errs:
                print(testinfo.name)
                print("Validaton errors:",errs)
            return testinfo
        except Exception as err:
            logging.warn(err)
        
    baselineExcels = list(EXPER_EXCEL.glob('*.xlsx'))
    
    print()    
    print(mdHeader(1,"Excel"))
    
    baselineExcelsTests = [ (f,test(f)) for f in EXPER_EXCEL.glob('*.xlsx') ]
    
    print()    
    print(mdHeader(1,"Images"))
    imageTest = [ (f,test(f)) for f in EXPER_SPECIMENIMAGES.glob('*') if f.is_dir() ]
    imageTestInfoCheck = [ (f,test(Path(f.name[len('DSC00208')+1:]))) for f in itertools.chain(*(d.glob('D*.info.JPG') for d in EXPER_SPECIMENIMAGES.glob('*') if d.is_dir())) ]
    
    print()
    print(mdHeader(1,EXPER_UTS_CSV.name))
    utsTest04 = [ (f,test(f)) for f in EXPER_UTS_CSV.glob('*') if f.is_dir() ]
    
    
    print()
    print(mdHeader(1,EXPER_PRELOAD_CSV.name))
    utsPreloads = [ (f,test(f)) for f in EXPER_PRELOAD_CSV.glob('*') if f.is_dir() ]
    
    print()
    print(mdHeader(1,EXPER_PRECONDS_CSV.name))
    utsPreconds = [ (f,test(f)) for f in EXPER_PRECONDS_CSV.glob('*') if f.is_dir() ]
    
    def lmap(func, iterable):
        return list(map(func,iterable))
        
    def grab(idx, iterable):
        return [ i[idx] for i in iterable if i[idx] ]
    
    
    toset = lambda fl: set(lmap(lambda x: x.short(), grab(1,fl)))
    baseline = toset(baselineExcelsTests)
    
    # debug(baseline)
    
    print()
    print(mdHeader(1, "Checking: Baselines"))
    
    def checkBaseline(baseline, name, fileList):
        print(mdHeader(2, "Checking: "+name))
        fileSet = toset(fileList)
        
        print(len(baseline), len(fileSet))
        
        # print()
        # for i,j,k in zip(sorted(baseline), sorted(fileSet), sorted(grab(0,fileList))):
        #     print(i,j, k.parent.name+'/'+k.name, sep=' | ')
        # print()
        
        diff = baseline-fileSet
        
        print("Missing in fileset:",diff,sep='\n')
        print("In: ", list((d,d in baseline) for d in diff))
    
    
    checkBaseline(baseline, 'images', imageTest)
    checkBaseline(baseline, 'utsPreloads', utsPreloads)
    checkBaseline(baseline, 'utsPreconds', utsPreconds)
    checkBaseline(baseline, 'utsTest04', utsTest04)
    
    # print(*baseline,sep='\n')
