#!/usr/bin/env python3

import os, sys, pathlib, re, collections
import pandas as pd
import numpy as np
import scipy.io as sio
from pandas import ExcelWriter

# sys.path.insert(0,[ str(p) for p in pathlib.Path('.').resolve().parents if (p/'scilab').exists() ][0] )


from scilab.tools.project import *
from scilab.expers.configuration import *
from scilab.tools.instroncsv import *
import scilab.tools.jsonutils as Json
import scilab.datahandling.columnhandlers as columnhandlers  

import numpy as np



get_attr_to_item = lambda xs: ''.join([ "['%s']"%x for x in xs.split('.')])
re_attribs = lambda k, s: re.sub(r"(%s)((?:\.\w+)+)"%k, lambda m: print(m.groups()) or m.groups()[0]+get_attr_to_item(m.groups()[1][1:]), s)
            

def isproperty(obj, key=None):
    return isinstance(obj, collections.Mapping) and (len(obj) == 1) and ((key in obj) if key else True)
    
    
def executeexpr(expr, **env):
    
    try:
        # print("executeexpr::expr: `{}`".format(expr))
        
        value = eval(expr, env)
        # print("executeexpr::result:", value,'\n')
        return value
    except Exception as err:
        print("error:executeexpr:env::",env.keys())
        raise err

def builtin_action_lookup(prop, **env):
    # debug(prop)
    keyexpr, values = getpropertypair(prop)
    # debug("builtin_action_lookup",keyexpr, values)
    keyvalue = executeexpr(keyexpr, **env)
    if keyvalue in values:
        return values[keyvalue]
    else:
        raise KeyError("_look_ failed: `{}` -> `{}` in {}".format(keyexpr, keyvalue, repr(list(values.keys()))))

@debugger
def userstrtopath(filepattern, testfolder):
    return resolve(matchfilename(testfolder.data, filepattern.format(**{})))
    
@debugger
def builtin_action_csv(filevalue, testfolder, **env):
    # filetype, filevalue = getpropertypair(prop)
    filepath = userstrtopath(filevalue, testfolder)
    data = csvread(filepath)
    filestruct = DataTree(path=filepath, data=data)
    return filestruct
    
def handle_builtin_actions(prop, env):
    key, value = getpropertypair(prop)
    debug(key, value,)
    if key == '_lookup_':
        return builtin_action_lookup(value, **env)
    elif key == '_csv_':
        return builtin_action_csv(getproperty(value, errorcheck=False, action=True, env=env), **env)
    else:
        raise KeyError("Unknown builtin: `{}`".format(key))

def getpropertypair(json_object):
    assert len(json_object) == 1
    return next(json_object.items().__iter__())

def getproperty(json_object, action=False, errorcheck=True, env=DataTree()):
    #if not isinstance(json_object, (dict, DataTree)):
    
    # print("getproperty::",repr(json_object), isproperty(json_object))

    if not isproperty(json_object):
        if errorcheck:
            raise ValueError(json_object, isinstance(json_object, collections.Mapping))
        else:
            return json_object
        
    if action and getpropertypair(json_object)[0].startswith('_'):
        return handle_builtin_actions(json_object, env=env)
    else:
        return next(json_object.values().__iter__())
    
def getpropertiesarray(json_array, errorcheck=True):
    return [ getproperty(item, errorcheck=errorcheck) for item in json_array ]

def clean(s):
    return s.replace("·",".")

class ProcessorException(Exception):
    pass
    
# @debugger
def assertsingle(xs):
    if len(xs) > 1:
        raise ProcessorException("assertsingle::Argument is not a single (e.g. len()==1). Has lenght: `{}`".format(len(xs)))
    elif len(xs) < 1:
        raise ProcessorException("assertsingle::Argument is not a single. It's empty. ")
    return xs

# @debugger
def matchfilename(testfolder, pattern, strictmatch=True):
    print(mdBlock("Matching pattern: `{}` in testfolder: `{}`, strictmatch: {} ", pattern, testfolder, strictmatch))
    files = sorted(testfolder.rglob(pattern))
    debug(files)
    if strictmatch:
        assertsingle(files)
    return files[-1]

# @debugger
def resolve(url):
    return Path(url).resolve()

def load_project_description(testfolder):
    ## temporary, later lookup test config
    project_description = Json.load_json_from(testfolder.projectdescription.resolve())    
    return project_description

def getfilenames(testfolder, stage, header, version, matlab=True, excel=True, numpy=False, pickle=True):
    hdrs = ''.join([ " {}={} |".format(*i) 
                    for i in sorted(flatten(header,ignore='filetype').items()) ])
    filename = testfolder.datacalc / 'data (stage={stage} |{header} v{ver}).txt'.format(stage=stage, header=hdrs, ver=version)
    
    filenames = DataTree()
    filenames.stage = stage
    filenames.version = version
    if matlab: filenames['names','matlab'] = filename.with_suffix('.mat')
    if excel: filenames['names','excel'] = filename.with_suffix('.xlsx')
    if numpy: filenames['names','numpy'] = filename.with_suffix('.npz')
    if pickle: filenames['names','pickle'] = filename.with_suffix('.pickle')

    return filenames
    
def getindexes(indexes, orderedmapping):
    """ function to make index data for a column. The inputs must be an array of dicts with column and the key type. 
    
    Outputting to matlab format, the keys must be valid variable/function names. So `some_name_1` but not `3.12`. 
    
    { 
        "column": "step",
        "type": "int",
    }
    """
    keyers = {
        'int':  lambda val: "idx_{}".format(int(val) if val >= 0 else "neg_"+str(abs(val))),
    }
        
    indexes = { index['column']: columnhandlers.getslices(
                                orderedmapping[index['column']],
                                keyer=keyers[index['type']],
                                astuple=True)
                            for index in indexes}
    
    return indexes
    
def save_columns(columnmapping, filenames, indexes=[{'column':'step','type':'int'}]):
    
    if not columnmapping:
        return 
    
    orderedmapping = OrderedDict( (k.name, v.array) for k,v in columnmapping ) 
    
    indexes = getindexes(indexes, orderedmapping)
    debug(indexes)
    
    if 'matlab' in filenames.names:
        save_columns_matlab(columnmapping, orderedmapping, indexes, filenames.names.matlab)
    if 'excel' in filenames.names:
        save_columns_excel(columnmapping, orderedmapping, indexes, filenames.names.excel)
    if 'numpy' in filenames.names:
        save_columns_numpy(columnmapping, orderedmapping, indexes, filenames.names.numpy)
    if 'pickle' in filenames.names:
        save_columns_pickle(columnmapping, orderedmapping, indexes, filenames.names.pickle)


def save_columns_matlab(columnmapping, orderedmapping, indexes, file):
    with open(str(file),'wb') as outfile:
        print("Writing matlab file...")
        matlabdata = {
            "data":orderedmapping, 
            "columninfo": { k.name: k for k,v in columnmapping },
            "summary": { k.name: v.summary for k,v in columnmapping },
            "indexes": indexes,
        }
         
        sio.savemat(outfile, matlabdata, 
                    appendmat=False, 
                    format='5',
                    long_field_names=False, 
                    do_compression=True,
                    )

def load_columns(filenames, filetype):
    return DataTree(
        matlab=load_columns_matlab,
        pickle=load_columns_pickle,
        json=load_columns_json,
    )[filetype](filenames[filetype])

def load_columns_matlab(filepath):
    print("Reading matlab file: `{}` ...".format(str(filepath)))
    debug(sio.whosmat(str(filepath)))
    print()
    
    # http://stackoverflow.com/questions/6273634/access-array-contents-from-a-mat-file-loaded-using-scipy-io-loadmat-python
    with open(str(filepath),'rb') as file:
        data = DataTree()
        sio.loadmat(file, mdict=data, squeeze_me=True, struct_as_record=False,)
        return data 
                       

def save_columns_numpy(columnmapping, orderedmapping, indexes, file):
    with open(str(file),'wb') as outfile:
        print("Writing numpy file...")
        np.savez_compressed(outfile, data=orderedmapping, columninfo={ k[0].name: k[0] for k in columnmapping }, indexes=indexes)

def save_columns_pickle(columnmapping, orderedmapping, indexes, file):
    import pickle
    with open(str(file),'wb') as outfile:
        print("Writing python pickle file...")
        pickle.dump({'data':orderedmapping, 'columninfo':{ k[0].name: k[0] for k in columnmapping }, 'indexes':indexes}, outfile)

def load_columns_pickle(filepath):
    import pickle
    with open(str(filepath),'rb') as file:
        print("Reading pickle file: `{}` ...".format(str(filepath)))
        return pickle.load(file)

def load_columns_json(filepath):
    return Json.load_json_from(filepath)

# @debugger
def save_columns_excel(columnmapping, orderedmapping, indexes, file):
    df1 = pd.DataFrame( orderedmapping )
    df2 = pd.DataFrame( [ k[0] for k in columnmapping ] )
    df3 = pd.DataFrame( [ [k]+list(v) for k,v in flatten(indexes,sep=".").items() ] )
    
    with ExcelWriter(str(file)) as writer:
        # [ENH: Better handling of MultiIndex with Excel](https://github.com/pydata/pandas/issues/5254)
        # [Support for Reading Excel Files with Hierarchical Columns Names](https://github.com/pydata/pandas/issues/4468)
        print("Creating excel file...")
        df1.to_excel(writer,'Data')
        df2.to_excel(writer,'ColumnInfo')
        df3.to_excel(writer,'Indexes')
        print("Writing excel file...")
        writer.save()

    