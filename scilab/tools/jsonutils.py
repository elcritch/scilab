#!/usr/bin/env python3

import os, tempfile, shutil, logging, re

import json as json

import jsonmerge
from pathlib import Path

if __name__ != '__main__':
    from scilab.tools.project import *
else:
    from project import *


def stems(file):
    return file.name.rstrip(''.join(file.suffixes))

if not hasattr(Path,'stems'):
    Path.stems = stems

def load_data_path(testpath, datadir="../../test-data/uts", dbg=None):

    datapath = testpath.parent.joinpath(datadir).resolve()
    testname = re.sub('(_[\w\d]+)$', '', testpath.parent.stems()) + '.json'

    debug(datapath, testname, testpath, testpath.parent.stems())
    if not (datapath / testname).exists():
        raise Exception("No json data for:\n"+'\n\t'.join(map(str,[testpath.stems(),datapath,testname])))

    data = load_json(datapath, json_url=testname)

    return data

def update_data_path(testpath, data, datadir="../../test-data/uts", dbg=None):
    
    datapath = testpath.parent.joinpath(datadir).resolve()
    testname = re.sub('(_\w+)$', '', testpath.parent.stems()) + '.json'
    
    debug(datapath, testname)
    update_json(datapath, data, json_url=testname)
    
    return


def load_data(parentdir, test_name, dataDir="../../test-data/", dbg=None):

    test_name = get_data_name(test_name)[0]

    dataDir = os.path.realpath(parentdir+"/"+dataDir)
    print("load_data:",dataDir)
    data = load_json(dataDir, json_url=test_name+".json")

    return data

def update_data(parentdir, test_name, data, dataDir="../../test-data/", dbg=None):
    test_name = get_data_name(test_name)[0]

    dataDir = os.path.realpath(parentdir+"/"+dataDir)
    print("update_data:",dataDir)
    update_json(dataDir, data, json_url=test_name+".json")

    return

# def load_json(parentdir, json_url="data.json"):
#
#     json_path = os.sep.join( [parentdir, json_url, ] )
#     with open( json_path ) as json_file:
#         json_data = json.load(json_file)
#
#         return json_data

    
def load_json_from(json_path, datatree=False, default=None):

    json_path = Path(str(json_path))
    
    try:
        with json_path.open() as json_file:

            dt = DataTree()
            def as_datatree(dct):
                tree = DataTree()
                tree.update(dct)
                return tree

            json_data = json.load(json_file, object_hook=as_datatree)
            # else:
            #     json_data = json.load(json_file)

            return json_data

    except Exception as err:

            try:
                # try print json raw
                with json_path.open() as json_file:
                    print(''.join(json_file.readlines()))
            except FileNotFoundError as err2:
                if default:
                    return default

                logging.warn("Json File not found: "+str(json_path))
                return None

            raise err

def load_json(parentdir, json_url="data.json", **kwargs):
    json_path = Path(str(parentdir)) / json_url
    return load_json_from(json_path, **kwargs)
    

import numpy

class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, numpy.ndarray):
                return obj.tolist()
            elif isinstance(obj, tuple) and hasattr(obj, '_fields'):
                return vars(obj)
            elif isinstance(obj, slice):
                return (obj.start, obj.step, obj.stop)
            elif isinstance(obj, numpy.generic):
                return numpy.asscalar(obj)
            else:
                # return super().default(obj)
                return json.JSONEncoder.default(self, obj)
                
        except TypeError as err:
            print("Json TypeError:"+str(type(obj))+" obj: "+str(obj))
            raise err

def write_json(parentdir,json_data, json_url="data.json", **kwargs):
    json_path = Path(str(parentdir)).resolve() / json_url
    return write_json_to(json_path=json_path, json_data=json_data, **kwargs)


@debugger
def write_json_to(json_path, json_data, dbg=None, ):

    json_path = Path(str(json_path))

    if dbg:
        debug(json_path, parentdir, json_path)

    with tempfile.NamedTemporaryFile('w',delete=False) as tempFile:

        if dbg:
            debug(json_path)
            print(json.dumps(json_data, indent=4))

        # with open( tempFile, 'w' ) as json_file:
        # with tempFile as json_file:
        json.dump(json_data, tempFile, indent=4, sort_keys=True, cls=CustomJsonEncoder)

            # update json file
            # debug(tempFile.name)

    if json_path.exists():
        json_path.unlink()

    os.rename(tempFile.name, str(json_path))

    return


def update_json(parentdir, update_data, json_url="data.json", default=None, dbg=None):
    """ Simple update method. Needs to handle merging better.  """

    json_data = load_json(parentdir,json_url=json_url, default=default)
    json_to_write = jsonmerge.merge(json_data, update_data)

    write_json(parentdir, json_to_write, json_url=json_url, dbg=dbg)

    return

def main():
    
    from collections import OrderedDict, namedtuple
    
    class NamedTuple():
        def set(self, **kw):
            vals = [ kw.get(fld, val) for fld,val in zip(self._fields, self) ]
            return self.__class__(*vals)
        # def __str__(self):
        #     return "{}({})".format(self.__class__.__name__, repr(self))
    

    class Test1(DataTree): 
        pass
    
    class Test2(object): 
        pass
    
    # debug(Test1(1,2).__class__.mro())
    
    j1 = { 'test1': Test1(a=1,b=2) }
    t1 = json.dumps(j1, sort_keys=True, cls=CustomJsonEncoder)
    # t2 = json.dumps(Test2(), sort_keys=True, cls=CustomJsonEncoder)
    t3 = CustomJsonEncoder().encode(Test1(a=5,b=6))
    debug(j1, t1, t3)
    
if __name__ == '__main__':
    main()
