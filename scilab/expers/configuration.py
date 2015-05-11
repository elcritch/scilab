#!/usr/bin/env python3

import shutil, re, sys, os, itertools, collections, logging, glob, time, shutil
from pathlib import Path
from functools import partial

if __name__ == '__main__':
    import os, sys, pathlib
    sys.path.insert(0,[ str(p) for p in pathlib.Path('.').resolve().parents if (p/'scilab').exists() ][0] )
    
from scilab.tools.project import *
from scilab.tools.helpers import *
import scilab.tools.jsonutils as Json

TestInfoTuple = collections.namedtuple('TestInfoTuple', 'name date batch side wedge orientation layer sample run')
TestParseTypes = tuple([ type( 'parse'+tp.__name__, (tp,), {}) for tp in (str, float, int) ])

def _parsevaluetry(val):
    """ tries to parse from least to most specific for str, float, int 
    
    returns a custom parse type for the type that allows setting attributes. """
    try:
        ret = val
        for pt in TestParseTypes:
            ret = pt(val)
    except:
        pass
    
    return ret


class BasicTestInfo(object):

    def validate(self):
        pass

    @property
    def short(self):
        return self._shortfmt.format(**self._asdict())
    
    @property
    def name(self):
        return self._fmt.format(**self._asdict())
        
    def differenceOf(self, that):
        toset = lambda ti: set( (k,v) for k,v in zip(ti._fields,ti))
        this, that = toset(self), toset(that)
        return that-this

    def __repr__(self):
        return "{name} [{short}]".format(name=self.name, short=self.short)
        
    def __str__(self):
        return "{short}".format(name=self.name, short=self.short)
        
    @classmethod
    def createfields(cls, valuedict):
        
        datafields = collections.OrderedDict()
        
        # for each field, process the matches
        for fieldname, fieldregex in cls._regexfields.items():
            
            # re-match all the subgroups
            fieldmatch = valuedict[fieldname]
            fieldgroups = fieldregex.match(fieldmatch).groups()                
            
            # set the main field values
            fieldvalue = _parsevaluetry( fieldmatch if fieldmatch else "")
            # set "match" attribute for matches for each subgroup
            fieldvalue.groups = [ _parsevaluetry(i) for i in fieldgroups ]
            datafields[ fieldname ] = fieldvalue
                    
        return datafields
        
    @classmethod
    def parse(cls, name):
        match = cls._regex.match(name)
        if match:
            # print("matched:", match.groupdict())
            return cls(**cls.createfields(valuedict=match.groupdict()))
        else:
            raise ValueError("Couldn't parse: ", name, cls._regex)



def generatetestinfoclass(
        prefix, 
        fields:list=[
            ("date",        "\w+\d+"),
            ("batch",       "..[\d\.]+"), 
            ],
        namefmt = "{date}({batch}-{side})-{wedge}-{orientation}-{layer}-{sample}-{run}",
        shortfmt = "{batch}-{wedge}{orientation}-{layer.groups[0]:d}{sample.groups[0]:02d}",
        ):
    
    prefix = "".join(prefix.capitalize() for x in prefix.split())
    classname = prefix+'TestInfo'
    AbbrevTestInfoTuple = collections.namedtuple(classname+"Tuple", [ f[0] for f in fields], rename=True)

    try:
        regexprfmt = namefmt.replace('(', '\(').replace(')', '\)').replace('[', '\[').replace(']', '\]')
        # debug(regexprfmt, fields)
        regexpression = regexprfmt.format(**{ k:"(?P<%s>%s)"%(k,v) for k,v in fields })
        # debug(regexpression)
        regexpression = re.compile(regexpression)
        # debug(regexpression)
    except Exception as err:
        raise err
        raise ValueError("Don't match:", fmt, fields)
    
    def __new__(cls, **kwargs):
        return AbbrevTestInfoTuple.__new__(cls, **cls.createfields(kwargs))
    
    def _asdict(self):
        return { f:v for f,v in zip(self._fields, self[:])}
        
    classtype = type(classname, (AbbrevTestInfoTuple, BasicTestInfo), 
                    dict( 
                            __new__ = __new__, _fmt = namefmt, _shortfmt = shortfmt,
                            _regex = regexpression, _asdict = _asdict, _regexfields = { k: re.compile(v) for k,v in fields } ,
                    ),
                )
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

    def __init__(self, projdescpath, verify=True, project=None, ):
        projdescpath = Path(str(projdescpath)).resolve()
        
        if not projdescpath.exists():
            raise Exception(projdescpath)
            
        projdesc = Json.load_json_from(projdescpath)
        self.projdesc = projdesc
        
        for i in ["testinfo", "testfolder", "projectfolder"]:
            key = ("experiment_config",i)
            if not projdesc[key]:
                print('Missing:\n\n    File "{key}", line 1, in {projdescpath}\n\n'.format(projdescpath=projdescpath, key=("experiment_config",i)), file=sys.stdout)
                raise ValueError("Missing config: ", key, projdescpath)
        
        self._testtnfo = generatetestinfoclass(**projdesc["experiment_config"]["testinfo"])
        
        names = self.projdesc.experiment_config.name.split('|')
        self.experiment_name = names[0]
        self.test_name = names[1:]

        self.project = projdescpath.parent if not project else project

        files = DataTree(projdesc.experiment_config.projectfolder.filestructure)
        self._files = self.parsefolders(files, verify, parent=self.project)
        for name, file in self._files.items():
            self[name] = file
    
    def parsefolders(self, files, verify, parent, env=DataTree(), makedirs=False):
        
        _files = DataTree()
        env.update(files)
        
        for foldername, folderitem in flatten(files, sort=True, tolist=True, astuple=True,):
            # debug( folderitem )
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
    
    def copyrawdir(self):
        
        assert "Not implemented yet!"
        
        if not rawdir.exists():
            logging.debug("Missing raw file: {}: {} raw: {}".format(name, test, rawdir))
            return
        
        sources = map(Path, glob.glob(str( rawdir / test)))
        sources = sorted( [ t for t in sources if t.is_dir() ], key=lambda x: x.stem, reverse=True)
        source = next(sources.__iter__(), None)
        if len(sources) > 1:
            logging.warn("Multiple raw test folders match, chose: %s from %s"%(
                            source.name, [ i.name for i in sources ]))
        
        return None
         
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

        folder = TestFileStructure(testdir=testdir)
        folder.update( self.parsefolders(tf.filestructure, verify, parent=testdir, env=testenv, makedirs=True) )
        
        # Handle Raw Data #
        for name, test in tf.raws.items():
            
            test = safefmt(test, raw=folder.raw, testinfo=testinfo)
            rawdir = Path(test)
            
            folder['raws',name] = rawdir

        # populate folder
        if ensure_folders_exists:
            for k, v in flatten(folder).items():
                # debug(k,v)
                if not v.exists():
                    v.mkdir()

        folder.update( self.parsefolders(tf.files, verify=False, parent=testdir, env=testenv) )
        
        if ensure_folders_exists:
            
            for tgtname, srcname in tf.templates.items():
                # debug(tgtname, srcname)
                srcpath = safefmt(str(srcname), testinfo=testinfo, filestructure=self)
                tgtpath = folder[tgtname]
                # debug(srcpath, tgtpath),
                
                shutil.copyfile(str(srcpath), str(tgtpath))
            
        return folder
    
    def makenewfolder(self, **kwargs):
        """ make a new test folder and populate it """        
        props = DataTree(date=time.strftime("%b%d"), run='').set(**kwargs)        
        testinfo = self._testtnfo(**props)
        
        testfolder = self.testfolder(testinfo=testinfo, makenew=True, ensure_folders_exists=True, verify=False)
        
        ## TODO: add post folder hooks, eg copy protocols into folder
        
        # TODO: implement copying template files... 
        
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
            ti = self._testtnfo.parse(str(item))
            if hasattr(ti, 'errors') and ti.errors:
                return None
            return ti
        except Exception as err:
            logging.warn("Could not parse test name: name: '%s' err: %s"%(str(item), str(err)))
            return None

ExampleTestInfo = generatetestinfoclass(
    "Example",
    fields=[
        ("errors",        "(\[.+?\]\s+)?"),
        ("date",        "\w+\d+"),
        ("batch",       "(..)(\d+)\.(\d+)"), 
        ("side",        "(l|r)(m|l)m"), 
        ("wedge",       "w([a-f])"), 
        ("orientation", "(tr|lg)"),
        ("layer",       "l(\d+)"),
        ("sample",      "x(\d+)"),
        ("run",         "(-.+)?"),
        ],
    namefmt = "{errors}{date}({batch}-{side})-{wedge}-{orientation}-{layer}-{sample}{run}",
    shortfmt = "{batch}-{wedge}{orientation}-{layer.groups[0]:d}{sample.groups[0]:02d}",
    )

  
def main():
    
    print("## Generating Testinfo Class")
    
    print(ExampleTestInfo)
    ti1 = ExampleTestInfo(date='dec01', run='', batch='gf10.1',side='llm',wedge='wa',orientation='lg',layer='l7',sample='x1', errors='')
    print("ti1:", ti1)

    ti2 = ExampleTestInfo.parse(name='dec01(gf10.1-llm)-wa-lg-l6-x1')
    print("ti2:", ti2)
    
    ti3 = ExampleTestInfo.parse(name='[unsure] dec01(gf10.1-llm)-wa-lg-l6-x1')
    print("ti3:", ti3.errors)
    
    print("## Loading Project Description")
    pdp = Path(__file__).parent/'../../test/fatigue-failure|uts|expr1/projdesc.json'
    pdp = pdp.resolve()
    print(pdp)
    
    import scilab.expers.mechanical.fatigue.uts as exper_uts
    
    fs = FileStructure(projdescpath=pdp, verify=True)

    ti = ExampleTestInfo.parse(name='dec01(gf10.1-llm)-wa-lg-l6-x1') # , date='dec01', run='', batch='gf10.1',side='llm',wedge='wa',orientation='lg',layer='l7',sample='x1')
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
    
    prevtestfolder = next(fs.tests.glob("may01*gf99.1*"), None)
    debug(fs.tests, prevtestfolder)
    if prevtestfolder:
        shutil.rmtree(str(prevtestfolder))
    
    newtestfolder = fs.makenewfolder(date="may01", batch='gf99.1',side='llm',wedge='wa',orientation='tr',layer='l7',sample='x1')
    
    print("### newtestfolder:")
    debug(newtestfolder)
    
    print("\nfolder:", sep='\n', *newtestfolder.testdir.glob("**/*"))
    
    # shutil.rmtree(str(newtestfolder.testdir), ignore_errors=True)
    
    
    
if __name__ == '__main__':
    main()


