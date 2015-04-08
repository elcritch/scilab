#!/usr/bin/env python3


import shutil, re, sys, os, itertools, collections, logging
from functools import partial

import scilab.tools.jsonutils as Json
from scilab.tools.project import *
from scilab.tools.helpers import *
from scilab.tools.excel import *

class TestInfo(collections.namedtuple('TestInfo', 'name date set side wedge orientation layer sample run')):

    reTestName = re.compile(r"(\w+\d+)\((..[\d\.]+)-(..m)\)-w([a-f])-(tr|lg)-l(\d+)-x(\d+)(?:-(.+))?")

    def __new__(self, name=None, *args, **kwargs):
        if name and not args and not kwargs:

            match = self.reTestName.match(name)
            if not match:
                raise Exception("Could not parse test name: "+name)

            args = match.groups()
            return super().__new__(self, name, *args)
        else:
            return super().__new__(self, name, *args, **kwargs)

    @property
    def short(self):
        """ Return a short mnemonic test name. """
        s = self
        strToOrd = lambda s: ''.join(str(ord(c.lower())-ord('a')+1) for c in s)
        batch, batchNumber = map(int,s.set[2:].split('.'))
        return "{0}{1:02d}-{2}{5}-{3:d}{4:02d}".format(
                batch, batchNumber, strToOrd(s.wedge),int(s.layer),int(s.sample), s.orientation.upper())

    def as_dict(self):
        return { f:v for f,v in zip(self._fields, self[:])}

    def validate(self):
        errors = []
        if self.side not in ('llm', 'lmm', 'rlm', 'rmm'):
            errors.append('Side incorrect:'+self.name)
        if self.wedge.lower() not in 'abcdef':
            errors.append('Wedge incorrect:'+self.name)
        if self.wedge.lower() not in 'af':
            errors.append('Wedge warning: not in common test: '+self.name)
        if not ( (self.wedge in 'abc' and self.side[1] == 'l')
                or (self.wedge in 'def' and self.side[1] == 'm') ):
            errors.append('Error! Wedge/Side mismatch: '+self.name+' '+self.side+' '+self.wedge)
        return errors

    def differenceOf(self, that):
        toset = lambda ti: set( (k,v) for k,v in zip(ti._fields,ti))
        this, that = toset(self), toset(that)
        return that-this

    def __str__(self):
        return "{name} ({short})".format(name=self.name, short=self.short)

def parser_data_sheet_excel(ws):
    
    rng = rangerForRow(ws)

    data = DataTree()
    data['info'] = DataTree()
    data['info'].update( dictFrom(rng('A1:B1')) )
    
    measurements = DataTree(withProperties='width depth area')
    measurements["width"] = valueUnitsStd(ws['B6'].value, units="mm", stdev=ws['B8'].value)._asdict()
    measurements["depth"] = valueUnitsStd(ws['C6'].value, units="mm", stdev=ws['C8'].value)._asdict()
    measurements["area"]  = valueUnits(ws['E6'].value, units="mm")._asdict()
    
    measurements["unadjusted","width"] = valueUnitsStd(ws['B7'].value, units="mm", stdev=ws['B8'].value)._asdict()
    measurements["unadjusted","depth"] = valueUnitsStd(ws['C7'].value, units="mm", stdev=ws['C8'].value)._asdict()
    measurements["unadjusted","area"]  = valueUnits(ws['E7'].value, units="mm")._asdict()
    
    # Process all the values in these rows
    other = DataTree()
    
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
    
    valueUnitsOverride = [ ('cycles', 'Nº Cycles'), ('precond_amp', 'mm'), ('precond_disp', 'mm'), ('uts', 'N') ]
    for key, units in valueUnitsOverride:
        other[key] = valueUnits(value=other[key], units=units)._asdict()
    
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

def main():

    print("Test TestInfo")

    ti = TestInfo(name='nov26(gf9.2-llm)-wf-tr-l9-x1')
    print(ti)

    ti = TestInfo('xx',*TestInfo.reTestName.match('nov26(gf9.2-rmm)-wf-tr-l9-x1-r1').groups())
    ti.short
    print(ti.short)

    print("Success")
    print()

    print("Good:")
    ti = TestInfo(name='nov26(gf9.2-rmm)-wf-tr-l9-x1-r1')
    print("Validate:", ti, ti.validate())
    print()
    ti = TestInfo(name='nov26(gf9.2-rlm)-wa-tr-l9-x1-r1')
    print("Validate:", ti, ti.validate())
    print()

    print("Fail:")
    ti = TestInfo(name='nov26(gf9.2-rlm)-wf-tr-l9-x1-r1')
    print("Validate:", ti, ti.validate())
    print()

    print("\nSet\n")
    # import Set
    ti = TestInfo(name='nov26(gf9.2-rlm)-wf-tr-l9-x1-r1')
    tj = TestInfo(name='nov26(gf9.2-rlm)-wa-tr-l9-x1-r1')

    si = set( (k,v) for k,v in zip(ti._fields,ti))
    sj = set( (k,v) for k,v in zip(tj._fields,tj))

    print(si)
    print(sj)
    print(si-sj)
    print(ti.differenceOf(tj))

    print("## FileStructure")
    fs = FileStructure('fatigue failure (cycles, expr1)', 'cycles-expr1')

    debug(fs)

    print("\n\nTests:\n\n",fs.testitemsd())


if __name__ == '__main__':
    main()


