#!/usr/bin/env python3

import os, sys, pathlib


# sys.path.insert(0,[ str(p) for p in pathlib.Path('.').resolve().parents if (p/'scilab').exists() ][0] )


from scilab.tools.project import *
from scilab.expers.configuration import *

import numpy as np


def data_normalize_col(testinfo:TestInfo, data:DataTree, details:DataTree, 
                    normfactor, xname, yname, yunits, balance, 
                    ):

    normalized = DataTree(steps=data.steps)
    if xname in data.summaries:
        normalized.summaries
    normalized.summaries.update(data_datasummaries(testinfo, data=data, details=details, cols=[xname]))
    
    # offset_load = data[loadname].array - data.summaries[xname].balance
    # normalized[loadname] = data[loadname].set(array=offset_load)
    
    ydata = data[dispname].array / normfactor
    normalized[stressname] = DataTree(array=stress, label=stressname.capitalize(), units=stressunits)

    normalized.summaries.update(data_datasummaries(testinfo, normalized, details, cols=[strainname, stressname]))

    normalized.summaries[strainname].balance = normalized.summaries[dispname].balance / details.gauge.value
    normalized.summaries[stressname].balance = normalized.summaries[loadname].balance / details.measurements.area.value
    
    return normalized


def process_columns(columns):
    
    pass
    
    
def process(file, kind, columnconfigs):
    
    
    
    
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
    
    