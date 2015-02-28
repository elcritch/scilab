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
        # debug(name)
        column = rawdata[name]
        
        # debug(column[1:])
        
        array, summary, *colinfo = column
        # print(tuple(colinfo))
        print(ColumnInfo(*colinfo).idx)
    
    if savemode == 'tracking':

        columns_renamed = [
           #ColumnInfo name                             label                  details                    units  full                                         idx
           #---------- ----------------------           ---------------------  -------------------------- -----  ----------------------------------------     ---- 
           ColumnInfo( 'load_1kN',                      'Load',                'Linear|Load',             'N',   'Load(Linear|Load) (N)',                       0),
           ColumnInfo(  None,                           'Total Cycle Count',   'Rotary Waveform',         'Nº',  'Total Cycle Count(Rotary Waveform)',          1),
           ColumnInfo( 'load_missus',                   'Load',                'Linear|The Missus',       'N',   'Load(Linear|The Missus) (N)',                 2),
           ColumnInfo( 'step',                          'Step',                '',                        'Nº',  'Step',                                        3),
           ColumnInfo( 'elapsedCycles',                 'Elapsed Cycles',      '',                        'Nº',  'Elapsed Cycles',                              4),
           ColumnInfo( 'disp',                          'Displacement',        'Linear|Digital Position', 'mm',  'Displacement(Linear|Digital Position) (mm)',  5),
           ColumnInfo(  None,                           'Position',            'Linear|Position',         'mm',  'Position(Linear|Position) (mm)',              6),
           ColumnInfo( 'totalCycleCount',               'Total Cycle Count',   'Linear Waveform',         'Nº',  'Total Cycle Count(Linear Waveform)',          7),
           ColumnInfo( 'totalTime',                     'Total Time',          '',                        's',   'Total Time (s)',                              8),
           ColumnInfo( 'cycleElapsedTime',              'Cycle Elapsed Time ', '',                        's',   'Cycle Elapsed Time (s)',                      9),
           ColumnInfo( 'totalCycles',                   'Total Cycles',        '',                        'Nº',  'Total Cycles',                               10),
        ]
        
        choose_stress_column_name = lambda info: 'load_1k' if info.orientation else 'load_missus'
        
        columns_normalized = [
            DataTree(name='strain', label='Strain', units='∆',   source='disp',                    factor=lambda info: 1.0/info.measurements.length),
            DataTree(name='stress', label='Stress', units='MPa', source=choose_stress_column_name, factor=lambda info: 1.0/info.measurements.area),
            DataTree(name='step',          source='step'),
            DataTree(name='elapsedCycles', source='elapsedCycles'),
            DataTree(name='totalCycleCount', source='totalCycleCount'),
            DataTree(name='totalTime', source='totalTime'),
            DataTree(name='cycleElapsedTime', source='cycleElapsedTime'),
            DataTree(name='totalCycles', source='totalCycles'),
        ]

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
    
    