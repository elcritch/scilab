#!/usr/bin/env python3

import sys, os, pathlib
sys.path.insert(0,[ str(p) for p in pathlib.Path('.').resolve().parents if (p/'scilab').exists() ][0] )

from scilab.tools.project import *
from scilab.tools.instroncsv import csvread
from scilab.tools.tables import *
from scilab.graphs.graph_shared import *

test_configs = {
    'preload_csv' :   DataTree(),
    'preconds_csv' :  DataTree(tracking=DataTree(balancestep='step_1')),
    'cycles_lg_csv' : DataTree(tracking=DataTree(balancestep='step_2')),
    'cycles_tr_csv' : DataTree(tracking=DataTree(balancestep='step_2')),
}

def handler(test:TestOverview, method_name, data_kind, datafile, args:DataTree):
    
    csvdata = csvread(str(datafile))
    # testname = 'cycles'
    # csvdata = testdata.tests[testname].tracking
    
    if data_kind == 'tracking':
    kws_balances = test_configs[method_name].get(data_kind, DataTree())
    
    data = data_configure_load(testinfo=test.info, data=csvdata, details=test.details, 
                               data_kind=data_kind, **kws_balances)
    
    updated = lambda d1,d2: [ d1.summaries[k].update(v) for k,v in d2.items() ]
    
    data.update( data_normalize(test.info, data, test.details) )
    
    debug(data)
    
    ## Save Summaries ##
    # testfolder.save_calculated_json(name='summaries', data={'step04_cycles':data.summaries})
    
    return {}

def process(testinfo, testfolder, **kwargs):
        
    args = DataTree()
    details = Json.load_json_from(testfolder.details)
    
    test = TestOverview(info=testinfo, folder=testfolder, details=details)
    
    # debug(test.folder.raws)

    for method_name, raw_data_files in test.folder.raws.items():
        for raw_data_kind, raw_data_file in raw_data_files.items():
            
            if not raw_data_file:
                continue
        
            debug(method_name, raw_data_kind, raw_data_file, sep=', ')
            
            handler(test, method_name, raw_data_kind, raw_data_file, args)
            
    # process_raw_csv(test, )
    
    # return handler(testinfo, testfolder, details=testdata.details, testdata=testdata, args=args, )

    
def main():
    
    import scilab.expers.mechanical.fatigue.cycles as fatigue_cycles
    import scilab.expers.mechanical.fatigue.uts as fatigue_uts
    
    fs = fatigue_cycles.FileStructure('fatigue failure (cycles, expr1)', 'cycles-expr2')
    # fs = fatigue_uts.FileStructure('fatigue failure (uts, expr1)', 'fatigue-test-2')
    # Test test images for now
    test_dir = fs.test_parent.resolve()
        
    testitemsd = fs.testitemsd()
    debug('\n'.join([l.name for l in testitemsd ]))
    
    tempreports = fs.results_dir/'Temp Reports'
    
    with (tempreports/'summary_all.log.md').open('w') as report:
    
        for testinfo, testfile  in list(testitemsd.items())[ :2 ]:
            
            try:
                testfolder = fs.testfolder(testinfo=testinfo)
                print(mdHeader(3, testinfo))
                res = process(testinfo, testfolder, reportfile=report)
            
            except Exception as err:
                logging.warn("Error processing tests %s: %s", testinfo, err)
                raise err
    

if __name__ == '__main__':

    main()


