#!/usr/bin/env python3

import os, sys, pathlib


# sys.path.insert(0,[ str(p) for p in pathlib.Path('.').resolve().parents if (p/'scilab').exists() ][0] )


from scilab.tools.project import *
from scilab.expers.configuration import *
from scilab.tools.instroncsv import *

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
    
    
def process_csv_file(rawdata, dataconfig):
    pass
    
def process_instron_file(csvpath,savemode,filekind):
    
    print(mdHeader(3, "File: {} ".format(csvpath.name) ))
    debug(locals())
    
    rawdata = csvread(csvpath)

    debug(rawdata.keys())
    
    # ColumnInfo('name label details units full idx')
    
    debug(rawdata.__class__.__name__)
    
    for name in rawdata.keys():
        debug(name)
        column = rawdata[name]
        
        debug(column[1:])
        
        array, summary, *colinfo = column
        print(tuple(colinfo))
    
    if savemode == 'tracking':

        rawcolumns = [
           #ColumnInfo  name                   label                  details                     units full
           #----------  ---------------------  ---------------------  --------------------------  ----- ----
            ColumnInfo('cycleElapsedTime',    'Cycle Elapsed Time ', '',                         's',  'Cycle Elapsed Time (s)',                      1),
            ColumnInfo('position',            'Position',            'Linear|Position ',         'mm', 'Position(Linear|Position) (mm)',              7),
            ColumnInfo('loadLinearTheMissus', 'Load',                'Linear|The Missus ',       'N',  'Load(Linear|The Missus) (N)',                11),
            ColumnInfo('displacement',        'Displacement',        'Linear|Digital Position ', 'mm', 'Displacement(Linear|Digital Position) (mm)',  9),
            ColumnInfo('elapsedCycles',       'Elapsed Cycles',      '',                         '',   'Elapsed Cycles',                              3),            
            ]

    

# "Total Time (s)",
# "Cycle Elapsed Time (s)",
# "Total Cycles",
# "Elapsed Cycles",
# "Step",
# "Total Cycle Count(Linear Waveform)",
# "Total Cycle Count(Rotary Waveform)",
# "Position(Linear:Position) (mm)",
# "Load(Linear:Load) (N)",
# "Displacement(Linear:Digital Position) (mm)",
# "Load(Linear:The Missus) (N)",

            
        # dataconfig = DataTree(url=csvname, columns='')

    elif savemode == 'trends':
        pass
    
def process_files(testfolder):
    
    for key, value in flatten(testfolder,sep='.').items():
        filekind, wavematrix, savemode = key.split('.')[1:]
        csvpath = value
        process_instron_file(csvpath=csvpath, savemode=savemode, filekind=filekind)
    
def main():
    
    samplefiles = Path(__file__).parent.resolve()/'..'/'..'/'test/instron-test-files'
    samplefiles = samplefiles.resolve()
    debug(samplefiles)
    
    ## create fake folder structure 
    testfolder = DataTree()
    testfolder['raw','csv','instron_test','tracking'] = samplefiles / 'instron-test-file.steps.tracking.csv' 
    testfolder['raw','csv','instron_test','trends'] = samplefiles / 'instron-test-file.steps.trends.csv' 

    process_files(testfolder)
    
if __name__ == '__main__':
    main()
    
    