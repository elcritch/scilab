#!/usr/bin/env python3

import shutil, re, sys, os, itertools, collections
from pathlib import Path
from functools import partial

if __name__ == '__main__':
    import os, sys, pathlib
    sys.path.insert(0,[ str(p) for p in pathlib.Path('.').resolve().parents if (p/'scilab').exists() ][0] )
    
from scilab.tools.project import *
from scilab.tools.helpers import *

class TestInfo(collections.namedtuple('TestInfo', 'name date set side wedge orientation layer sample run')):

    def __new__(self, reTestName=None, name=None, *args, **kwargs):
        if name and not args and not kwargs:

            match = self.reTestName.match(name)
            if not match:
                raise Exception("Could not parse test name: "+name)

            args = match.groups()
            return super().__new__(self, name, *args)
        else:
            return super().__new__(self, name, *args, **kwargs)

    def validate(self):
        pass

    def short(self):
        pass
    
    def _strToOrd(s): 
        return ''.join(str(ord(c.lower())-ord('a')+1) for c in s)

    def as_dict(self):
        return { f:v for f,v in zip(self._fields, self[:])}

    def differenceOf(self, that):
        toset = lambda ti: set( (k,v) for k,v in zip(ti._fields,ti))
        this, that = toset(self), toset(that)
        return that-this

    def __str__(self):
        return "{name} ({short})".format(name=self.name, short=self.short())

class ImageSet(collections.namedtuple('TestSet', 'info, front, side, fail')):
    pass

class FileStructure(DataTree):

    def __init__(self, experiment_name:str, test_name):

        self.experiment_name = experiment_name
        self.test_name = test_name

        self.project = None
        for path in Path('.').resolve().parents:
#            print(path.name, self.experiment_name)
            if path.name == self.experiment_name:
                self.project = path

        if not self.project:
            raise Exception("Could not find experiment (project) path: "+experiment_name)

        project = self.project
        raw = self.raw = self.project / '01_Raw'

        self.raws = DataTree()
        self.raws.preload_csv    = raw / '01 Preloads'
        self.raws.preconds_csv   = raw / '02 Preconditions'
        self.raws.cycles_lg_csv     = raw / '03 Fatigue Cycles (LG)'
        self.raws.cycles_tr_csv     = raw / '03 Fatigue Cycles (TR)'

        self.test_parent         = project / '02_Tests' / self.test_name
        self.results_dir         = project / '04_Results'

        for name in (self.test_parent, self.results_dir, self.raw):
            logging.info("FileStructure: Resolving: "+str(name))
            name.resolve()

    def testfolder(self, testinfo:TestInfo, ensure_folders_exists=False):
        test_dir = self.test_parent / testinfo.name

        def findFilesIn(testfolder, pattern='*', kind='png'):
            return list( testfolder.glob('{pattern}.{kind}'.format(**locals())) )

        folder = DataTree()
        folder.project_dir = self.project
        folder.testfs = self
        folder.graphs         = test_dir / 'graphs'
        folder.json           = test_dir / 'json'
        folder.jsoncalc       = folder.json / 'calculated'
        folder.images         = test_dir / 'images'
        folder.raws           = self.findRaws(testinfo)
        folder.datasheet      = next(test_dir.glob('data_sheet*.xlsx'), None)
    
        if ensure_folders_exists:
            for v in sorted(folder.values(), key=lambda x: str(x)):
                if not v.exists():
                    v.mkdir()

        return folder

    def findRaws(self, testinfo):
        
        testraws = DataTree()
        for name, datafolder in self.raws.items():            
            testraws[name] = self.findTestCsv(testinfo, datafolder)
        
        return testraws

    def testitemsd(self):

        folders = [ (self.infoOrNone(f.name), f)
                        for f in self.test_parent.glob('*')
                            if f.is_dir() ]
        folders = [ (i,f) for i,f in folders if i ]
        folders = sorted(folders, key=lambda item: item[0].short() )
        folderd = collections.OrderedDict(folders)

        return folderd


    def infoOrNone(self, item):
        try:
            return TestInfo(name=str(item))
        except Exception as err:
            logging.warn("Could not parse test name: name: '%s' err: %s"%(str(item), str(err)))
            return None

    def findTestCsv(self, testinfo, rawfolder):
                        
        globfiles = rawfolder.glob( testinfo.name+'*' )
        
        testfolders = sorted( [ t for t in globfiles if t.is_dir() ], key=lambda x: x.stem)
        
        if not testfolders:
            return DataTree(tracking=None, trends=None, stop=None)
        
        testfolder = testfolders[-1]
        
        if len(testfolders) > 1:
            logging.warn("Multiple csv test folders match, chose: %s from %s"%(testfolder.name, [ i.name for i in testfolders ]))
        
        tracking = next(testfolder.glob('*.tracking.csv'),None)
        trends   = next(testfolder.glob('*.trends.csv'),None)
        stop     = next(testfolder.glob('*.stop.csv'),None)
        
        # if tracking or trends or stop:
        return DataTree(tracking=tracking, trends=trends, stop=stop)
        # else:
            # return DataTree()

class TestData(DataTree):
    
    # def __init__(self, *args, **kwargs):
        # super().__init__(*arg, **kwargs)
        
    def __str__(self):
        return "TestData[%s]"%super().__str__()
    
class TestDetails(DataTree):

    # def __init__(self, *args, **kwargs):
        # super().__init__(*arg, **kwargs)

    def __str__(self):
        return "TestDetails[%s]"%super().__str__()

class TestOverview(DataTree):
    pass

def main():
    
    pass

    # print("Test TestInfo")
    #
    # ti = TestInfo(name='nov26(gf9.2-llm)-wf-tr-l9-x1')
    # print(ti)
    #
    # ti = TestInfo('xx',*TestInfo.reTestName.match('nov26(gf9.2-rmm)-wf-tr-l9-x1-r1').groups())
    # ti.short()
    # print(ti.short())
    #
    # print("Success")
    # print()
    #
    # print("Good:")
    # ti = TestInfo(name='nov26(gf9.2-rmm)-wf-tr-l9-x1-r1')
    # print("Validate:", ti, ti.validate())
    # print()
    # ti = TestInfo(name='nov26(gf9.2-rlm)-wa-tr-l9-x1-r1')
    # print("Validate:", ti, ti.validate())
    # print()
    #
    # print("Fail:")
    # ti = TestInfo(name='nov26(gf9.2-rlm)-wf-tr-l9-x1-r1')
    # print("Validate:", ti, ti.validate())
    # print()
    #
    # print("\nSet\n")
    # # import Set
    # ti = TestInfo(name='nov26(gf9.2-rlm)-wf-tr-l9-x1-r1')
    # tj = TestInfo(name='nov26(gf9.2-rlm)-wa-tr-l9-x1-r1')
    #
    # si = set( (k,v) for k,v in zip(ti._fields,ti))
    # sj = set( (k,v) for k,v in zip(tj._fields,tj))
    #
    # print(si)
    # print(sj)
    # print(si-sj)
    # print(ti.differenceOf(tj))
    #
    # print("## FileStructure")
    # fs = FileStructure('fatigue failure (cycles, expr1)', 'cycles-expr1')
    #
    # debug(fs)
    #
    # print("\n\nTests:\n\n",fs.testitemsd())


if __name__ == '__main__':
    main()


