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

import numpy as np


get_attr_to_item = lambda xs: ''.join([ "['%s']"%x for x in xs.split('.')])
re_attribs = lambda k, s: re.sub(r"(%s)((?:\.\w+)+)"%k, lambda m: print(m.groups()) or m.groups()[0]+get_attr_to_item(m.groups()[1][1:]), s)
            

def isproperty(obj, key=None):
    return isinstance(obj, collections.Mapping) and (len(obj) == 1) and (key in obj) if key else True
    
def getproperty(json_object):
    assert len(json_object) == 1
    return next(json_object.values().__iter__())

def getpropertypair(json_object):
    assert len(json_object) == 1
    return next(json_object.items().__iter__())

def getproperties(json_array):
    return [ getproperty(item) for item in json_array ]

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

def userstrtopath(filepattern, testconfig):    
    return resolve(matchfilename(testconfig.folder.data, filepattern.format(**testconfig.info)))
    
def action_csv(filevalue, action, testconfig):
    filepath = userstrtopath(filevalue, testconfig)
    debug(filepath)
    data = csvread(filepath)
    return data

    
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
    
def save_columns(columnmapping, filenames):
    
    if not columnmapping:
        return 
    
    orderedmapping = OrderedDict( (k.name, v.array) for k,v in columnmapping ) 
    
    if 'matlab' in filenames.names:
        save_columns_matlab(columnmapping, orderedmapping, filenames.names.matlab)
    if 'excel' in filenames.names:
        save_columns_excel(columnmapping, orderedmapping, filenames.names.excel)
    if 'numpy' in filenames.names:
        save_columns_numpy(columnmapping, orderedmapping, filenames.names.numpy)
    if 'pickle' in filenames.names:
        save_columns_pickle(columnmapping, orderedmapping, filenames.names.pickle)

def save_columns_matlab(columnmapping, orderedmapping, file):
    with open(str(file),'wb') as outfile:
        print("Writing matlab file...")
        sio.savemat(outfile, {"data":orderedmapping, "columns": { k[0].name: k[0] for k in columnmapping } } , 
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
        sio.loadmat(file,mdict=data,squeeze_me=True, struct_as_record=False,)
        return data 
                       

def save_columns_numpy(columnmapping, orderedmapping, file):
    with open(str(file),'wb') as outfile:
        print("Writing numpy file...")
        np.savez_compressed(outfile, data=orderedmapping, columns={ k[0].name: k[0] for k in columnmapping })

def save_columns_pickle(columnmapping, orderedmapping, file):
    import pickle
    with open(str(file),'wb') as outfile:
        print("Writing python pickle file...")
        pickle.dump({'data':orderedmapping, 'columns':{ k[0].name: k[0] for k in columnmapping }}, outfile)

def load_columns_pickle(filepath):
    import pickle
    with open(str(filepath),'rb') as file:
        print("Reading pickle file: `{}` ...".format(str(filepath)))
        return pickle.load(file)

def load_columns_json(filepath):
    return Json.load_json_from(filepath)

# @debugger
def save_columns_excel(columnmapping, orderedmapping, file):
    df1 = pd.DataFrame( orderedmapping )
    df2 = pd.DataFrame( [ k[0] for k in columnmapping ] )
    
    with ExcelWriter(str(file)) as writer:
        # [ENH: Better handling of MultiIndex with Excel](https://github.com/pydata/pandas/issues/5254)
        # [Support for Reading Excel Files with Hierarchical Columns Names](https://github.com/pydata/pandas/issues/4468)
        print("Creating excel file...")
        df1.to_excel(writer,'Data')
        df2.to_excel(writer,'ColumnInfo')
        print("Writing excel file...")
        writer.save()

    