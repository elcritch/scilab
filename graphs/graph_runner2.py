#!/usr/bin/env python3
# coding: utf-8

import sys, os, glob, logging
import itertools, functools
from pathlib import Path

import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt

curr = Path('.').resolve()
for path in Path('.').resolve().parents:
    print("path:",path, (path / 'scilab').exists())
    if (path / 'scilab').exists():
        scibase = path

print("scibase:",scibase)
sys.path.insert(0,str(scibase))

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
# from scilab.expers.mechanical.fatigue.uts import FileStructure
# from scilab.expers.mechanical.fatigue.uts import TestInfo as TestInfo
from scilab.expers.mechanical.fatigue.helpers import *
import scilab.tools.json as Json

from scilab.expers.mechanical.fatigue.cycles import TestInfo

PlotData = namedtuple('PlotData', 'array label units max')

def findTestCsv(csvTestParent, testfile):
    debug(csvTestParent, testfile)

    testfiles = [ t for t in csvTestParent.glob(testfile+'*') if t.is_dir() ]
    if not testfiles:
        raise Exception("Cannot find matching csv test folder: "+testfile+" "+csvTestParent.as_posix())
    elif len(testfiles) > 1:
        testfile = sorted(testfiles, key=lambda x: x.stem )[0]
        logging.warn("Multiple csv test files match, choosing: "+str(testfile) )
        return testfile
    else:
        return testfiles[0]
    
def process_uts_tests(testinfo, testfolder, handlers, reportfile):
    args = DataTree()
    args.experReportGraphs = testfolder.graphs
    args.experJson = testfolder.jsoncalc
    args.experJsonCalc = testfolder.jsoncalc
    args.only_first = False
    args.report = reportfile    
    args.step = 2
    args.begin = 80.3
    args.end = 4.8
    
    data = DataTree()
    data.tests = DataTree()
    
    trackingtest = testfolder.raws.csv_step04_uts.tracking
    trackingdata = csvread(trackingtest.as_posix())
    data.tracking = trackingdata
    
    data.tests.uts = DataTree(tracking=trackingdata)
    debug(testfolder.raws.csv_step02_precond.tracking)
    data.tests.preconds = DataTree(tracking = csvread( testfolder.raws.csv_step02_precond.tracking ))    
    data.datasheet = testfolder.datasheet
    
    data.details = Json.load_json_from(testfolder.details)
    
    return [ handler(testinfo=testinfo, testfolder=testfolder, testdata=data, args=args)
                for handler in handlers ]

    measurements = run_image_measure.process_test(testinfo, testfolder)
    
    

def process_cycle_tests(testinfo, testfolder, handlers, reportfile):
    args = DataTree()
    args.experReportGraphs = testfolder.graphs
    args.experJson = testfolder.jsoncalc
    args.experJsonCalc = testfolder.jsoncalc
    args.only_first = False
    args.report = reportfile
    
    doLoad = DataTree(trackingtest=False)
    

    
    data = DataTree()
    
    if doLoad.trackingtest:
        if testinfo.orientation == 'lg':
            trackingtest = testfolder.raws.cycles_lg_csv.tracking
        else:
            trackingtest = testfolder.raws.cycles_tr_csv.tracking
        
        if trackingtest:
            debug(trackingtest)
            data.tracking = csvread(trackingtest.as_posix())            
        else:
            logging.error("ERROR: instron_all.py: Could not find tracking test csv file for: "+str(testinfo))
            return None
    
    data.datasheet = testfolder.datasheet
    data.details = Json.load_json_from(testfolder.details)

    results = []
    for handler in handlers:
        results.append( handler(testinfo=testinfo, testfolder=testfolder, testdata=data, args=args) )
        
    return results    

def process_test(testinfo, testfolder, reportfile):

    debug(testinfo, testinfo)

    import scilab.utilities.make_data_json as make_data_json
    import scilab.utilities.merge_calculated_jsons as merge_calculated_jsons
    import scilab.expers.mechanical.fatigue.run_image_measure as run_image_measure
    import scilab.graphs.instron_uts as graphs_instron_uts
    import scilab.graphs.precondition_fitting as precondition_fitting 
    import scilab.graphs.cycle_trends as cycle_trends 
    
    cycle_handlers = [ 
            # make_data_json.graphs2_handler,
            # merge_calculated_jsons.graphs2_handler,
            cycle_trends.graphs2_handler,
        ]
    
    uts_handlers = [
            # run_image_measure.graphs2_handler,
            # make_data_json.graphs2_handler,
            # merge_calculated_jsons.graphs2_handler,
            # graphs_instron_uts.graphs2_handler,
            precondition_fitting.graphs2_handler,
            merge_calculated_jsons.graphs2_handler,
        ]
    
    return process_cycle_tests(testinfo, testfolder, cycle_handlers, reportfile)
    # return process_uts_tests(testinfo, testfolder, uts_handlers, reportfile)


# from multiprocessing import Pool

def main():
    
    fs = FileStructure('fatigue failure (cycles, expr1)', 'cycles-expr2')
    # fs = FileStructure('fatigue failure (uts, expr1)', 'fatigue-test-2')
    # Test test images for now
    test_dir = fs.test_parent.resolve()
    
    
    testitemsd = fs.testitemsd()

    import seaborn as sns
    sns.set_style("whitegrid")
    # sns.set_style("ticks")
    # sns.set_style("dark")
    
    testitems = list(testitemsd.items())
    debug('\n'.join([l.name for l in testitemsd ]))
    
    tempreports = fs.results_dir/'Temp Reports'
    if not tempreports.is_dir():
        tempreports.mkdir()
    
    with (tempreports/'Excel Data Sheet Results.md').open('w') as report:
    
        # for testinfo, testfile  in testitems[ : ]:
        for testinfo, testfile  in testitems[ :2 ]:
            
        # for testinfo, testfile  in testitems[ : len(testitems)//2 ]:
        # for testinfo, testfile  in testitems[ len(testitems)//2-1 : ]:

            # if testinfo.orientation == 'lg':
            # if testinfo.orientation == 'tr':
                # continue
            # if testinfo.name != 'nov28(gf10.1-llm)-wa-tr-l4-x2':
            #     continue
            
            testfolder = fs.testfolder(testinfo=testinfo, ensure_folders_exists=False)
            
            print(mdHeader(3, testinfo))
            
            try:
                res = process_test(testinfo, testfolder, reportfile=report)
                print(res)
            
            except Exception as err:
                logging.warn("Error processing tests %s: %s", testinfo, err)
                raise err
    

if __name__ == '__main__':

    main()

