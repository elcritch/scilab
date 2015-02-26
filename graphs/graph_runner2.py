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
from scilab.tools.instroncsv import *

import scilab.tools.project as Project
import scilab.tools.excel as Excel
import scilab.tools.graphing as Graphing
import scilab.tools.scriptrunner as ScriptRunner
import scilab.tools.jsonutils as Json

from scilab.tools.tables import mdBlock, mdHeader, ImageTable, MarkdownTable
from scilab.expers.mechanical.fatigue.helpers import *
from scilab.expers.configuration import FileStructure, TestInfo, TestData, TestDetails

import scilab.expers.mechanical.fatigue.cycles as fatigue_cycles
import scilab.expers.mechanical.fatigue.uts as fatigue_uts


PlotData = namedtuple('PlotData', 'array label units max')
    
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
    # debug(testfolder.raws.csv_step02_precond.tracking)
    data.tests.preconds = DataTree(tracking = csvread( testfolder.raws.csv_step02_precond.tracking ))    
    data.datasheet = testfolder.datasheet
    
    data.details = Json.load_json_from(testfolder.details)
    
    return [ handler(testinfo=testinfo, testfolder=testfolder, testdata=data, args=args)
                for handler in handlers ]

    measurements = run_image_measure.process_test(testinfo, testfolder)
    
    

def process_cycle_tests(testinfo, testfolder, reportfile, doLoad, handlers,):
    args = DataTree()
    args.experReportGraphs = testfolder.graphs
    args.experJson = testfolder.jsoncalc
    args.experJsonCalc = testfolder.jsoncalc
    args.only_first = False
    args.report = reportfile
    args.doLoad = doLoad
    
    testdata = TestData(tests=TestData())
    
    # debug(testfolder.raws.preconds_csv.tracking)
    testdata.tests.preconds = DataTree(tracking = csvread( testfolder.raws.preconds_csv.tracking ))    

    cycles_test = 'cycles_{}_csv'.format(testinfo.orientation)
    debug(cycles_test, testfolder.raws[cycles_test].tracking)
    testdata.tests.cycles = TestData()
    if doLoad.tracking:
        csvdata_tracking = csvread(testfolder.raws[cycles_test].tracking.as_posix())
        testdata.tests.cycles.tracking = csvdata_tracking
    if doLoad.trends:
        csvdata_trends = csvread(testfolder.raws[cycles_test].trends.as_posix())
        testdata.tests.cycles.trends = csvdata_trends

    testdata.details = Json.load_json_from(testfolder.details)
    
    results = []
    for handler in handlers:
        results.append( handler(testinfo=testinfo, testfolder=testfolder, testdata=testdata, args=args) )
        
    return results    

def process_test(testinfo, testfolder, reportfile):

    debug(testinfo, testinfo)

    import scilab.utilities.make_data_json as make_data_json
    import scilab.utilities.merge_calculated_jsons as merge_calculated_jsons
    import scilab.expers.mechanical.fatigue.run_image_measure as run_image_measure
    import scilab.graphs.instron_uts as graphs_instron_uts
    import scilab.graphs.instron_all as graphs_instron_all
    import scilab.graphs.graph_all as graphs_graph_all
    import scilab.graphs.precondition_fitting as precondition_fitting
    import scilab.graphs.cycle_trends as cycle_trends
    
    doLoadTracking = DataTree(tracking=True, trends=False)
    doLoadTrends   = DataTree(tracking=False, trends=True)
    doLoadPost     = DataTree(tracking=False, trends=False)
    
    try:
        # process_cycle_tests(testinfo, testfolder, reportfile, doLoadTracking,
        #                     handlers=[make_data_json.graphs2_handler, merge_calculated_jsons.graphs2_handler], )
        #
        # process_cycle_tests(testinfo, testfolder, reportfile, doLoadTracking,
        #                     handlers=[ graphs_graph_all.graphs2_handler,merge_calculated_jsons.graphs2_handler,], )
        #
        # process_cycle_tests(testinfo, testfolder, reportfile, doLoadTrends,
        #                     handlers=[cycle_trends.graphs2_handler], )

        process_cycle_tests(testinfo, testfolder, reportfile, doLoadPost,
                            handlers=[merge_calculated_jsons.graphs2_handler], )
        
        # return process_uts_tests(testinfo, testfolder, uts_handlers, reportfile)
    except Exception as err:
        # logging.warn("Error occurred: "+str(err),exc_info=err)
        raise err

# from multiprocessing import Pool

def main():
    
    fs = fatigue_cycles.FileStructure('fatigue failure (cycles, expr1)', 'cycles-expr2')
    # fs = fatigue_uts.FileStructure('fatigue failure (uts, expr1)', 'fatigue-test-2')
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
    
        for testinfo, testfile  in testitems[ : ]:
        # for testinfo, testfile  in testitems[ :2 ]:
        # for testinfo, testfile  in testitems[ : len(testitems)//2 ]:
        # for testinfo, testfile  in testitems[ len(testitems)//2-1 : ]:

            # if testinfo.orientation == 'lg':
            # if testinfo.orientation == 'tr':
                # continue
            # if testinfo.name != 'nov28(gf10.1-llm)-wa-tr-l4-x2':
            #     continue
            
            testfolder = fs.testfolder(testinfo=testinfo, ensure_folders_exists=False)
            
            print(mdHeader(3, testinfo))
            
            # if any( testfolder.jsoncalc.glob('*.summaries.calculated.json') ):
            #     logging.info("SKIPPING: "+str(testinfo))
            #     continue
            
            try:
                res = process_test(testinfo, testfolder, reportfile=report)
                print(res)
            
            except Exception as err:
                logging.warn("Error processing tests %s: %s", testinfo, err)
                raise err
    

if __name__ == '__main__':

    main()

