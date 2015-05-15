#!/usr/bin/env python3


import shutil, re, sys, os, itertools, collections, logging
from functools import partial

import scilab.tools.jsonutils as Json
from scilab.tools.project import *
from scilab.tools.helpers import *
from scilab.tools.excel import *
import scilab.datahandling.processingpreconditioning 

def parser_data_sheet_excel(ws, testconf):
    
    rng = rangerForRow(ws)

    data = DataTree()
    data['info'] = DataTree()
    data['info'].update( dictFrom(rng('A1:B1')) )
    
    measurements = DataTree(withProperties='width depth area')
    
    # Process all the values in these rows
    other = DataTree()
    
    other["width"] = valueUnitsStd(ws['B6'].value, units="mm", stdev=ws['B8'].value)._asdict()
    other["depth"] = valueUnitsStd(ws['C6'].value, units="mm", stdev=ws['C8'].value)._asdict()
    other["area"]  = valueUnits(ws['E6'].value, units="mm")._asdict()
    
    other["unadjusted","width"] = valueUnitsStd(ws['B7'].value, units="mm", stdev=ws['B8'].value)._asdict()
    other["unadjusted","depth"] = valueUnitsStd(ws['C7'].value, units="mm", stdev=ws['C8'].value)._asdict()
    other["unadjusted","area"]  = valueUnits(ws['E7'].value, units="mm")._asdict()
    
    # -- tr / lg correlation curves --
    testcorr = lambda *data: all(data)
    
    def findcorrs():
        corrs = DataTree(lg=None, tr=None)
        for (colA,colB) in [('D','F'), ('E','G')]:
            for idx in range(16,20):
                corrs["lg"] = DataTree(linearFit(ws['%s%d'%(colA,idx)].value, ws['%s%d'%(colB,idx)].value)._asdict())
                corrs["tr"] = DataTree(linearFit(ws['%s%d'%(colA,idx+2)].value, ws['%s%d'%(colB,idx+2)].value)._asdict())
        
                try:
                    corrs["lg",]["slope"] = float(corrs["lg",]["slope"])
                    corrs["lg",]["intercept"] = float(corrs["lg",]["intercept"])
                    corrs["tr",]["slope"] = float(corrs["tr",]["slope"])
                    corrs["tr",]["intercept"] = float(corrs["tr",]["intercept"])
                except: 
                    continue
                           
                debug(colA, colB, corrs)
                if all([corrs["lg",]["slope"], corrs["lg",]["slope"], corrs["tr",]["intercept"], corrs["tr",]["intercept"]]):
                    return corrs
                
    corrs = findcorrs()
    
    print("final:")
    debug(corrs)
    if not all( isinstance(corrs[idx],float) for idx in [ ["lg","slope"], ["lg","slope"], ["tr","intercept"], ["tr","intercept"]]):
        raise ValueError("utscorrelation not found in datasheet")
    
    other["utspredcorrelation"] = corrs[testconf.info.orientation]
    
    ## continue reading the column down 
    end = process_definitions_column(ws, other, 'A',9,24, stop_key='UTS Stress', dbg=False, has_units=False)    
    # debug(end, other.keys())
    
    # startUnitValues = [ i for i in ( 20, 21, 22, 23 ) if 'uts stress' in ws["A"+str(i)].tolower() ][0]
    end = process_definitions_column(ws, other, 'A', end, 50, stop_key='Failure Notes / Test Results', dbg=False, has_units=True)

    # debug(end, other.keys())
    assert "uts_stress" in other.keys()
    assert "est_stress_(tr)" in other.keys()
    assert "gauge_base" in other.keys()
    assert "estimated_amp" in other.keys()
    assert "actual_sl" in other.keys()
    
    valueUnitsOverride = [ ('precond_amp', 'mm'), ('precond_disp', 'mm'), ('uts', 'N') ]
    for key, units in valueUnitsOverride:
        other[key] = valueUnits(value=other[key] if key in other else float('nan'), units=units)._asdict()
    
    if 'area' in other:
        other.pop('area')
    
    debug(other)
    
    # gauge
    gauge = measurements['gauge',] = DataTree()
    
    units = 'mm' # default
    
    if 'gauge' in other:
        gauge.length = valueUnits(other.pop('gauge'), units)._asdict()
    
    if 'gauge_init' in other:
        gauge.init_position = valueUnits(other.pop('gauge_init'), units)._asdict()
    else:
        raise Exception("Excel file missing gauge_base! Possible keys:\t"+str([ str(k) for k in other.keys() ]) )
    
    if 'gauge_base' in other:
        gauge.base = valueUnits(other.pop('gauge_base'), units)._asdict()
    else:
        raise Exception("Excel file missing gauge_base! Possible keys:\t"+str([ str(k) for k in other.keys() ]) )
    
    # handle cycles
    cycles = other.pop("cycles")
    debug(cycles)
    cyclestop, cyclesbottom = str(cycles["value"]), str(cycles["units"])
    other["cyclesRunOut"] = True if '+' in cyclestop or '+' in cyclesbottom else False    
    other["cyclesTop"] = valueUnits(int(cyclestop.strip().strip('+')), units="Nº")._asdict()
    other["cyclesBottom"] = valueUnits(int(cyclesbottom.strip().strip('+')), units="Nº")._asdict()
    
    # setup excel other
    data['excel','other'] = other
    data['measurements','datasheet'] = measurements
    
    debug(data.keys())
    # data.measurements.area.value = other.pop('area')
    
    notes = {}
    process_definitions_column(ws, notes, 'A', end+1,end+5, stop_key=None, dbg=None)
    data['excel','notes'] = notes
    
    return data
        
def parser_image_measurements(testconf, imgdata):
        
    data = DataTree()
    data['info'] = DataTree()
    data['info'].update( testconf.info.as_dict() )
    data['info']['set'] = testconf.info.name
    
    # debug('\n'.join(map(str,flatten(imgdata,sep='.').items())))
    
    measurements = DataTree(width=DataTree(), depth=DataTree(), area=DataTree())
    measurements.width.value = imgdata.front.mm.summaries.widths.average.mean
    
    if not 'side' in imgdata:
        logging.warn("Could not find side measurement for: "+str(testconf.info))
        measurements.depth.value = 1.00
        measurements.depth.stdev = -1.0
    else:
        measurements.depth.value = imgdata.side.mm.summaries.widths.average.mean
        measurements.depth.stdev = imgdata.side.mm.summaries.widths.average.std
        
    measurements.area.value = float(measurements.width.value)*float(measurements.depth.value)
    
    measurements.width.stdev = imgdata.front.mm.summaries.widths.average.std
    
    measurements.width.units = 'mm'
    measurements.depth.units = 'mm'
    measurements.area.units = 'mm^2'
    
    measurements.image = DataTree(other={})
    
    for k in 'front side fail'.split():
        measurements.image.other[k] = imgdata[k].mm.other if k in imgdata else {}
    
    data['measurements','image'] = measurements
    
    return data

def getcodehandlers():
    
    def process_utspred(tangent_modulus, details, projectdesc):
        
        
        projdesc.experiment_config.config.calibration.utsprediction.all[details.info.orientation]
        
        
    
    return DataTree(process_precondition=scilab.datahandling.processingpreconditioning.process_precondition)
    


