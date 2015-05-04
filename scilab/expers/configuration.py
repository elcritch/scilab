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

TestInfoTuple = collections.namedtuple('TestInfoTuple', 'name date batch side wedge orientation layer sample run')

class BasicTestInfo(object):

    def validate(self):
        pass

    @property
    def short(self):
        return self.format(**self._asdict())
    
    @property
    def name(self, **kwargs):
        return self._fmt.format(self._asdict())
        
    def differenceOf(self, that):
        toset = lambda ti: set( (k,v) for k,v in zip(ti._fields,ti))
        this, that = toset(self), toset(that)
        return that-this

    def __str__(self):
        print("str:self:",self._asdict(), self[:])
        return self._fmt.format(**self._asdict())
        
    @classmethod
    def parse(cls, name):
        print("regex:", cls._regex, "fields:", cls._fields, "\n")
        match = cls._regex.match(name)
        if match:
            print("matched:", match.groupdict())
            return cls(**match.groupdict())
        else:
            raise ValueError("Couldn't parse: ", name, cls._regex)



def generatetestinfoclass(
        description, 
        fields:tuple=[
            ("date",        "\w+\d+"),
            ("batch",       "..[\d\.]+"), 
            ("side",        "..m"), 
            ("wedge",       "w[a-f]"), 
            ("orientation", "tr|lg"), 
            ("layer",       "l\d+"), 
            ("sample",      "x\d+"), 
            ("run",         "(?:-.+)?"),
            ],
        fmt = "{date}({batch}-{side})-{wedge}-{orientation}-{layer}-{sample}-{run}",
        ):
    
    description = "".join(description.capitalize() for x in description.split())
    classname = description+'TestInfo'
    AbbrevTestInfoTuple = collections.namedtuple(classname+"Tuple", [ f[0] for f in fields], rename=True)

    try:
        regexprfmt = fmt.replace('(', '\(').replace(')', '\)').replace('[', '\[').replace(']', '\]')
        debug(regexprfmt, fields)
        regexpression = regexprfmt.format(**dict(fields)) 
        regexpression = re.compile(regexpression)
        debug(regexpression)
    except Exception as err:
        raise err
        raise ValueError("Don't match:", fmt, fields)
    
    def __new__(cls, **kwargs):
        return AbbrevTestInfoTuple.__new__(cls, **kwargs)
    
    def _asdict(self):
        return { f:v for f,v in zip(self._fields, self[:])}
        
    classtype = type(classname, (AbbrevTestInfoTuple, BasicTestInfo), 
                        dict( __new__ = __new__, _fmt = fmt, _regex = regexpression, _asdict = _asdict ))
    # globals()[classname] = classtype
        
    # type(nameprefix+'TestInfo')
    return classtype
    

class TestFileStructure(DataTree):

    def load(self,name='details'):
        
        data = Json.load_json_from(testfolder.self[name])
        
        return data

    def get_calculated_json_name(self, test, name, suffix="calculated", field="{name}", **kwargs):
        return "{short}.{name}.{suffix}json".format(
                    short=test.info.short,
                    name=name,
                    suffix = suffix+"." if suffix else "",
                    )
    
    def save_calculated_json(self, test, name, data, **kwargs):
        return self.save_calculated_json_raw(test, name, {name:data}, **kwargs)
        
    def save_calculated_json_raw(self, test, name, json_data, field="{name}", **kwargs):
        filename = self.get_calculated_json_name(test, name, field=field, **kwargs)
        
        json_path = self.jsoncalc / filename
        
        print("Saving json file `{filename}` into the test's TestFileStructure".format(filename=filename))
        print("Saving json file `{filename}` with fields: {fields}".format(
                filename=filename, fields=', '.join( flatten(json_data,sep='.').keys() ) ))
        
        if kwargs.get('overwrite', False) == True:
            ret = Json.write_json_to(json_path=json_path, json_data=json_data, **kwargs)
        else:
            ret = Json.update_json_at(update_path=json_path, update_data=json_data, **kwargs)
        
        return (json_path, ret)
    
    def save_graph_raw(self, testinfo, version, name:str, fig, imgkind="png", savefig_kws=DataTree(bbox_inches='tight')):
        
        namefmt = "{testname} | name={name} | test={testinfo} | {version}.{imgkind}"
        
        filename = namefmt.format(
                name=name,
                testname=testconf.info.name,
                testinfo=testconf.info.short,
                version=testconf.folder.version,
                imgkind=imgkind,
                )
        
        imgpath = self.graphs / filename
        print("Saving json file `filename` into the test's TestFileStructure".format(filename=filename))
        
        return (imgpath, fig.savefig(str(imgpath), **savefig_kws))
        
    def save_graph(self, filename, fig, savefig_kws=DataTree(bbox_inches='tight')):
                
        imgpath = self.graphs / filename
        print("Saving json file `filename` into the test's TestFileStructure".format(filename=filename))
        
        return fig.savefig(str(imgpath), **savefig_kws)
        
class FileStructure(DataTree):

    def __init__(self, projdescpath, testinfo, verify=True, project=None):
        projdescpath = Path(str(projdescpath)).resolve()
        
        if not projdescpath.exists():
            raise Exception(projdescpath)
            
        projdesc = Json.load_json_from(projdescpath)
        self.projdesc = projdesc
        self._testtnfo = testinfo
        
        names = self.projdesc.experiment_config.name.split('|')
        self.experiment_name = names[0]
        self.test_name = names[1:]

        self.project = projdescpath.parent if not project else project

        if not (self.project / '.git').is_dir():
            logging.warn("No git folder present for project: {}".format(self.project))
            if verify:
                raise Exception("No git folder present!")

        files = DataTree(projdesc.experiment_config.projectfolder.filestructure)
        self._files = self.parsefolders(files, verify, parent=self.project)
        for name, file in self._files.items():
            self[name] = file
    
    def parsefolders(self, files, verify, parent, env=DataTree(), makedirs=False):
        
        _files = DataTree()
        env.update(files)
        
        for foldername, folderitem in flatten(files, sort=True, tolist=True):
            debug( folderitem )
            folder = parent / folderitem.format(**env).strip()
            
            if makedirs and not folder.exists():
                os.makedirs( folder.as_posix() )
                
            if verify:
                try:
                    folder = folder.resolve()
                except FileNotFoundError as err:
                    raise FileNotFoundError("Folder: `{}`".format(folder))
                
            _files[foldername] = folder
        
        return _files
        
    def testfolder(self, testinfo:BasicTestInfo, ensure_folders_exists=False, makenew=False, verify=False):
        
        tf = DataTree(self.projdesc["experiment_config"]["testfolder"])
        
        testdir = Path(tf['folder'].format(testinfo=testinfo, **self._files))
        
        if makenew and testdir.exists():
                raise ValueError("Cannot make a new test folder. Directory exist. ", testdir)
        elif makenew:
                os.makedirs( str(testdir) )
        elif verify:
                raise ValueError("Test Directory does not exist. ", testdir)            
        
        testenv = DataTree(folder=testdir, testinfo=testinfo)

        folder = TestFileStructure()
        folder.update( self.parsefolders(tf.filestructure, verify, parent=testdir, env=testenv, makedirs=True) )
        folder.update( self.parsefolders(tf.files, verify=False, parent=testdir, env=testenv) )
        
        # Handle Raw Data #
        for name, test in tf.raws.items():
            
            test = safefmt(test, raw=folder.raw, testinfo=testinfo)
            rawdir = Path(test)
            
            if not rawdir.exists():
                logging.debug("Missing raw file: {}: {} raw: {}".format(name, test, rawdir))
                continue
            
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
    
    def makenewfolder(self, **kwargs):
        props = DataTree(date='may02', run='').set(**kwargs)        
        testinfo = TestInfo(name=TestInfo.format(**props), **props)
        
        testfolder = self.testfolder(testinfo=testinfo, makenew=True, ensure_folders_exists=True, verify=False)
        
        ## TODO: add post folder hooks, eg copy protocols into folder
        
        ## Bam, done...     
    
        return testfolder

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
    
    print("## Generating Testinfo Class")
    ExampleTestInfo = generatetestinfoclass(
        "Example",
        fields=[
            ("date",        "(\w+\d+)"), 
            ("batch",       "(..[\d\.]+)"), 
            ("side",        "(..m)"), 
            ("wedge",       "w([a-f])"), 
            ("orientation", "(tr|lg)"), 
            ("layer",       "l(\d+)"), 
            ("sample",      "x(\d+)"), 
            ("run",         "(-.+)?"),
            ],
        fmt = "{date}({batch}-{side})-{wedge}-{orientation}-{layer}-{sample}{run}",
    )
    
    print(ExampleTestInfo)
    ti1 = ExampleTestInfo(date='dec01', run='', batch='gf10.1',side='llm',wedge='wa',orientation='lg',layer='l7',sample='x1')
    print("ti1:", ti1)

    ti2 = ExampleTestInfo.parse(name='dec01(gf10.1-llm)-wa-lg-l6-x1')
    print("ti2:", ti2)
    
    print("## Loading Project Description")
    pdp = Path(__file__).parent/'../../test/fatigue-failure|uts|expr1/projdesc.json'
    pdp = pdp.resolve()
    print(pdp)
    
    import scilab.expers.mechanical.fatigue.uts as exper_uts
    
    fs = FileStructure(projdescpath=pdp,testinfo=exper_uts.TestInfo, verify=True)

    ti = TestInfo(name='dec01(gf10.1-llm)-wa-lg-l6-x1', date='dec01', run='', batch='gf10.1',side='llm',wedge='wa',orientation='lg',layer='l7',sample='x1')
    debug(ti._asdict())
    debug(ti)
    tf = fs.testfolder(ti)
    
    print("## Test: TF ##")
    for k,v in flatten(tf).items():
        print("key:",k, '\n', "val:",v.relative_to(pdp.parent) if isinstance(v,Path) else v,'\n')

    print("## Test: testitemsd ##")
    
    tests = fs.testitemsd()
    
    for test in tests:
        print("test:", test,'\n')

    print("## Verify Make New Test")
    
    newtestfolder = fs.makenewfolder(batch='gf10.1',side='llm',wedge='wa',orientation='tr',layer='l7',sample='x1')
    
    print("newtestfolder:", newtestfolder)
    
    # os.rmtree(newtestfolder.testdir)
    
    
    
    
if __name__ == '__main__':
    main()


