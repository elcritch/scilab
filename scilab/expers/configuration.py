#!/usr/bin/env python3

import shutil, re, sys, os, itertools, collections, logging, glob
from pathlib import Path
from functools import partial

if __name__ == '__main__':
    import os, sys, pathlib
    sys.path.insert(0,[ str(p) for p in pathlib.Path('.').resolve().parents if (p/'scilab').exists() ][0] )
    
from scilab.tools.project import *
from scilab.tools.helpers import *
import scilab.tools.jsonutils as Json

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
        return "{name} ({short})".format(name=self.name, short=self.short)

class ImageSet(collections.namedtuple('TestSet', 'info, front, side, fail')):
    pass

class TestFileStructure(DataTree):

    def load(self,name='details'):
        
        data = Json.load_json_from(testfolder.self[name])
        
        return data

    def save_calculated_json(self, test, name, data, **kwargs):
        return self.save_calculated_json_raw(test, name, {name:data}, **kwargs)
        
    def save_calculated_json_raw(self, test, name, json_data, suffix="calculated", field="{name}", **kwargs):
        filename = "{short}.{name}.{suffix}json".format(
                    short=test.info.short,
                    name=name,
                    suffix = suffix+"." if suffix else "",
                    )
        
        json_path = self.jsoncalc / filename
        
        print("Saving json file `{filename}` into the test's TestFileStructure".format(filename=filename))
        print("Saving json file `{filename}` with fields: {fields}".format(
                filename=filename, fields=', '.join( flatten(json_data,sep='.').keys() ) ))
        
        return Json.update_json_at(update_path=json_path, update_data=json_data, **kwargs)
    
    def save_graph(self, name:str, fig, imgkind="png", savefig_kws=DataTree(bbox_inches='tight')):
        
        namefmt = "{testname} | name={name} | test={testinfo} | {version}.{imgkind}"
        
        filename = namefmt.format(
                name=name,
                testname=self.testfs.test_name,
                testinfo=self._testinfo.short,
                version=self.testfs.version,
                imgkind=imgkind,
                )
        
        imgpath = self.graphs / filename
        print("Saving json file `filename` into the test's TestFileStructure".format(filename=filename))
        
        return fig.savefig(str(imgpath), **savefig_kws)
        
class FileStructure(DataTree):

    def __init__(self, projdescpath, testinfo, verify=True):
        projdescpath = Path(str(projdescpath)).resolve()
        
        if not projdescpath.exists():
            raise Exception(projdescpath)
            
        projdesc = Json.load_json_from(projdescpath)
        self.projdesc = projdesc
        self._testtnfo = testinfo
        
        names = self.projdesc.experiment_config.name.split('|')
        self.experiment_name = names[0]
        self.test_name = names[1:]

        self.project = projdescpath.parent

        if not (self.project / '.git').is_dir():
            logging.warn("No git folder present for project: {}".format(self.project))
            if verify:
                raise Exception("No git folder present!")

        files = DataTree(projdesc.experiment_config.projectfolder.filestructure)
        self._files = self.parsefolders(files, verify, parent=self.project)
        for name, file in self._files.items():
            self[name] = file
    
    def parsefolders(self, files, verify, parent, env=DataTree()):
        
        _files = DataTree()
        env.update(files)
        
        for foldername, folderitem in flatten(files, sort=True, tolist=True):
            folder = parent / folderitem.format(**env).strip()
            if verify:
                try:
                    folder = folder.resolve()
                except FileNotFoundError as err:
                    raise FileNotFoundError("Folder: `{}`".format(folder))
                
            _files[foldername] = folder
        
        return _files
        
    def testfolder(self, testinfo:TestInfo, ensure_folders_exists=False, verify=False):
        
        tf = DataTree(self.projdesc.experiment_config.testfolder)
        
        testdir = Path(tf['folder'].format(testinfo=testinfo, **self._files))
        testenv = DataTree(folder=testdir,testinfo=testinfo)

        folder = TestFileStructure()
        folder.update( self.parsefolders(tf.filestructure, verify, parent=testdir, env=testenv) )
        folder.update( self.parsefolders(tf.files, verify=False, parent=testdir, env=testenv) )
        
        # Handle Raw Data #
        for name, test in tf.raws.items():
            
            test = safefmt(test, raw=folder.raw)
            rawdir = Path(test)
            
            if not rawdir.exists():
                debughere("Missing raw file: {}: {} raw: {}".format(name, test, rawdir))
                
            sources = map(Path, glob.glob(str( rawdir / test)))
            sources = sorted( [ t for t in sources if t.is_dir() ], key=lambda x: x.stem, reverse=True)
            source = next(sources.__iter__(), None)
            if len(sources) > 1:
                logging.warn("Multiple raw test folders match, chose: %s from %s"%(
                                source.name, [ i.name for i in sources ]))
            
            folder['raws',name] = source
    
        if ensure_folders_exists:
            for v in sorted(folder.values(), key=lambda x: str(x)):
                if not v.exists():
                    v.mkdir()

        return folder

    def testitemsd(self):

        folders = [ (self.infoOrNone(f.name), f)
                        for f in self.tests.glob('*')
                            if f.is_dir() ]
        folders = [ (i,f) for i,f in folders if i ]
        folders = sorted(folders, key=lambda item: item[0].short )
        folderd = collections.OrderedDict(folders)

        return folderd


    def infoOrNone(self, item):
        try:
            return self._testtnfo(name=str(item))
        except Exception as err:
            logging.warn("Could not parse test name: name: '%s' err: %s"%(str(item), str(err)))
            return None

def main():
    pdp = Path(__file__).parent/'../../test/fatigue-failure|uts|expr1/projdesc.json'
    pdp = pdp.resolve()
    print(pdp)
    
    import scilab.expers.mechanical.fatigue.uts as exper_uts
    
    fs = FileStructure(projdescpath=pdp,testinfo=exper_uts.TestInfo, verify=True)

    ti = DataTree(name='dec01(gf10.1-llm)-wa-lg-l6-x1')
    tf = fs.testfolder(ti)
    
    print("## Test: TF ##")
    for k,v in flatten(tf).items():
        print("key:",k, '\n', "val:",v.relative_to(pdp.parent) if isinstance(v,Path) else v,'\n')

    print("## Test: testitemsd ##")
    
    tests = fs.testitemsd()
    
    for test in tests:
        print("test:", test,'\n')
    
    
if __name__ == '__main__':
    main()


