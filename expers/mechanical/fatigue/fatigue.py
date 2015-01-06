#!/usr/bin/env python3


import shutil, re, sys, os, itertools, collections
from pathlib import Path

import scilab.tools.json as Json 
from scilab.tools.project import *
from scilab.tools.helpers import *

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
            

    def short(self):
        """ Return a short mnemonic test name. """
        s = self
        strToOrd = lambda s: ''.join(str(ord(c.lower())-ord('a')+1) for c in s)
        batch, batchNumber = map(int,s.set[2:].split('.'))
        return "{0}{1:02d}{5}-{2}{3:02d}{4}".format(
                batch, batchNumber, strToOrd(s.wedge),int(s.layer),s.sample, s.orientation.upper())

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
        return "{name} ({short})".format(name=self.name, short=self.short())

class ImageSet(collections.namedtuple('TestSet', 'info, front, side, fail')):
    pass
    


class FileStructure(DataTree):
    
    def __init__(self, project_name:str, experiment_name:str, expers_override:dict={}):
        
        self.valid_experiments = {
            'fatigue failure (UTS, exper1)': ('uts (expr-1)'),
            }
            
        self.valid_experiments.update(expers_override)
        
        self.project_name = project_name
        self.experiment_name = experiment_name

        self.projects = Path(RESEARCH) / '07_Experiments'
        self.project  = projectspath / self.projectName
    
        self.instron = DataTree()
        self.instron.preload_csv    = project / '01 (uts) preloads' 
        self.instron.preconds_csv   = project / '02 (uts) preconditions' 
        self.instron.uts_csv        = project / '04 (uts) uts-test' 
    
        self.exper_data             = projectpath / 'test-data'/ self.experimentName
        
        self.expers = DataTree()
        self.expers.excel          = exper_data / '01 Excel' 
        self.expers.json           = exper_data / '00 JSON'
        self.expers.report         = exper_data / '02 Reports'
        self.expers.reportgraphs   = exper_data / '03 Graphs'
        self.expers.jsoncalc       = exper_json / 'calculated'
        self.expers.specimenimages = exper_data / '05 Specimen Images' / '02 Test Images'
    
    def exists(self):
        return { n:d.exists() for n,d in  }

def main():
    
    print("Test UtsTestInfo")
    
    ti = UtsTestInfo(name='nov26(gf9.2-llm)-wf-tr-l9-x1')
    print(ti)
    
    ti = UtsTestInfo('xx',*UtsTestInfo.reTestName.match('nov26(gf9.2-rmm)-wf-tr-l9-x1-r1').groups())
    ti.short()
    print(ti.short())
    
    print("Success")
    print()
    
    print("Good:")
    ti = UtsTestInfo(name='nov26(gf9.2-rmm)-wf-tr-l9-x1-r1')
    print("Validate:", ti, ti.validate())
    print()
    ti = UtsTestInfo(name='nov26(gf9.2-rlm)-wa-tr-l9-x1-r1')
    print("Validate:", ti, ti.validate())
    print()
    
    print("Fail:")
    ti = UtsTestInfo(name='nov26(gf9.2-rlm)-wf-tr-l9-x1-r1')
    print("Validate:", ti, ti.validate())
    print()

    print("\nSet\n")
    # import Set
    ti = UtsTestInfo(name='nov26(gf9.2-rlm)-wf-tr-l9-x1-r1')
    tj = UtsTestInfo(name='nov26(gf9.2-rlm)-wa-tr-l9-x1-r1')
    
    si = set( (k,v) for k,v in zip(ti._fields,ti))
    sj = set( (k,v) for k,v in zip(tj._fields,tj))
    
    print(si)
    print(sj)
    print(si-sj)
    print(ti.differenceOf(tj))

    
if __name__ == '__main__':
    main()
    
    
