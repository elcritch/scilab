#!/usr/bin/env python3

import os, sys, pathlib, re, collections, glob
import pandas as pd
import numpy as np
import scipy.io as sio
from pandas import ExcelWriter

# sys.path.insert(0,[ str(p) for p in pathlib.Path('.').resolve().parents if (p/'scilab').exists() ][0] )


from scilab.tools.project import *
from scilab.expers.configuration import *
from scilab.tools.instroncsv import *
import scilab.tools.jsonutils as Json
import scilab.tools.datacleanup as datacleanup 
import scilab.datahandling.columnhandlers as columnhandlers  

import numpy as np



get_attr_to_item = lambda xs: ''.join([ "['%s']"%x for x in xs.split('.')])
re_attribs = lambda k, s: re.sub(r"(%s)((?:\.\w+)+)"%k, lambda m: print(m.groups()) or m.groups()[0]+get_attr_to_item(m.groups()[1][1:]), s)
            

def isproperty(obj, key=None):
    return isinstance(obj, collections.Mapping) and (len(obj) == 1) and ((key in obj) if key else True)
    
    
def executeexpr(expr, **kwargs):
    
    try:
        print("executeexpr::expr: `{}`".format(expr))
        
        helpers = DataTree( asval=columnhandlers.asvalue, getvar=columnhandlers.getvar )
        
        env = helpers+kwargs
        value = eval(expr, env)
        
        # print("executeexpr::result:", value,'\n')
        return value
    except NameError as err:
        raise NameError(err, "Variables available: {}".format(list(env.keys())), expr)
    except Exception as err:
        # debughere()
        raise Exception(err, "Expression: {}".format(expr))

def builtin_action_lookup(prop, **env):
    # debug(prop)
    keyexpr, values = getpropertypair(prop)
    # debug("builtin_action_lookup",keyexpr, values)
    keyvalue = executeexpr(keyexpr, **env)
    if keyvalue in values:
        return values[keyvalue]
    else:
        raise KeyError("_look_ failed: `{}` -> `{}` in {}".format(keyexpr, keyvalue, repr(list(values.keys()))))

def calcenv():
    calc = DataTree()
    for name, item in vars(np).items():
        calc[name] = item
    
    for name, item in vars(columnhandlers).items():
        calc[name] = item    

    calc["findendpoint"] = datacleanup.calculate_data_endpoint2
    return calc

def builtin_action_exec(values, **env):

    calc = calcenv()
    
    # debug("builtin_action_exec",values)
    results = DataTree()
    env["vars"] = results
    
    try:
        flat_values = sorted(flatten(values, astuple=True, tolist=True), key=lambda x: x[0] )
            
        for varname, expr in flat_values:
            if varname in results:
                raise NameError("Variable name already exists, cannot overwrite: `{varname}`".format(varname=varname))
            
            results[varname] = executeexpr(expr, calc=calc, **env)
            
    except Exception as err:
        debug(repr(locals().get('flat_values',values)))
        raise err
        
    return results

@debugger
def userstrtopath(filepattern, env):
    return resolve(matchfilename(filepattern.format(**env)))
    
@debugger
def builtin_action_csv(filevalue, **env):
    # filetype, filevalue = getpropertypair(prop)
    
    # filepath = userstrtopath(filevalue, env)
    try:
        data = csvread(filevalue)
        filestruct = DataTree(path=filevalue, data=data)
    except Exception as err:
        logging.error(err)
        raise Exception("Error reading csv file", filevalue, )
        
    return filestruct
    
def handle_builtin_actions(prop, env):
    try:
        key, value = getpropertypair(prop)
        # debug(key, value,)
        if key == '_lookup_':
            return builtin_action_lookup(value, **env)
        elif key == '_csv_':
            return builtin_action_csv(getproperty(value, errorcheck=False, action=True, env=env), **env)
        elif key == '_exec_':
            return builtin_action_exec(value, **env)
        else:
            raise KeyError("Unknown builtin: `{}`".format(key))
    except Exception as err:
        # debughere()
        raise err

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
def matchfilename(pattern, strictmatch=True):
    print(mdBlock("Matching pattern: `{}` strictmatch: {} ", pattern, strictmatch))
    files = sorted(map(Path, glob.glob(pattern)), reverse=True)
    debug(files)
    if strictmatch:
        assertsingle(files)
    return next(files.__iter__(), None)

# @debugger
def resolve(url):
    return Path(url).resolve()

def load_project_description(testfolder):
    ## temporary, later lookup test config
    project_description = Json.load_json_from(testfolder.projectdescription.resolve())    
    return project_description

def getfileheaders(name, test, headers, version, suffix='txt'):
    hdrs = flatten(header,ignore='filetype').items() if isinstance(headers, dict) else headers
    
    hdrs = ''.join([ " {}={} |".format(*i) 
                    for i in hdrs ])
    
    debug(hdrs)
    
    filename = "{name} (test={short} | {header} v{ver}).{suffix}".format(
            name=name, short=test.info.short, header=hdrs, ver=version,
            suffix=suffix,
            )
    
    return filename
    

def getfilenames(test, testfolder, stage, header, version, matlab=True, excel=True, config=False, numpy=False, pickle=False, json=False):
    hdrs = ''.join([ " {}={} |".format(*i) 
                    for i in flatten(header,ignore='filetype').items() ])
    filename = testfolder.data / 'data (test={short} | stage={stage} |{header} v{ver}).txt'.format(
                    short=test.info.short, stage=stage, header=hdrs, ver=version)
    
    filenames = DataTree()
    filenames.stage = stage
    filenames.version = version
    if matlab: filenames['names','matlab'] = filename.with_suffix('.mat')
    if excel: filenames['names','excel'] = filename.with_suffix('.xlsx')
    if numpy: filenames['names','numpy'] = filename.with_suffix('.npz')
    if pickle: filenames['names','pickle'] = filename.with_suffix('.pickle')
    if json: filenames['names','json'] = filename.with_suffix('.json')
    if config: filenames['names','config'] = filename.with_suffix('.config.json')

    return filenames

print("datahandlers")

def datacombinations(test, args,
                     stages = ["raw", "norm"],
                     methods = ["precond", "uts", "preload"],
                     items = ["tracking","trends"],
                     ):
    
    datafiles = DataTree()
    for (stage, method, item) in itertools.product(stages, methods, items):
    
        header = OrderedDict(method=method, item=item)

        files = getfilenames(
            test=test, testfolder=test.folder, stage=stage, 
            version=args.version, header=header, matlab=True, excel=False)
    
        # debug(files.names.matlab)
        # debug(files.names.matlab.exists())
        
        datafiles[(stage, method, item)] = files.names.matlab
    
    # debug(datafiles)
    
    return datafiles


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
    
def save_columns(columnmapping, filenames, configuration, indexes=[{'column':'step','type':'int'}]):
    
    if not columnmapping:
        raise Exception("Nothing to save!")
    
    orderedmapping = OrderedDict( (k.name, v.array) for k,v in columnmapping )
    indexes = getindexes(indexes, orderedmapping)
    # debug(indexes)
    
    for filetype, filepath in filenames.names.items():
        parent = Path(str(filepath)).parent 
        if not parent.exists():
            print("Info:: Making parent directory: {parent}")
            os.makedirs(str(parent))
    
    try:
        if 'matlab' in filenames.names:
            save_columns_matlab(columnmapping, orderedmapping, configuration, indexes, filenames.names.matlab)
        if 'excel' in filenames.names:
            save_columns_excel(columnmapping, orderedmapping, configuration, indexes, filenames.names.excel)
        if 'numpy' in filenames.names:
            save_columns_numpy(columnmapping, orderedmapping, configuration, indexes, filenames.names.numpy)
        if 'pickle' in filenames.names:
            save_columns_pickle(columnmapping, orderedmapping, configuration, indexes, filenames.names.pickle)
        if 'json' in filenames.names:
            save_columns_json(columnmapping, orderedmapping, configuration, indexes, filenames.names.json)
        if 'config' in filenames.names:
            save_columns_json_config(columnmapping, orderedmapping, configuration, indexes, filenames.names.config)
    except Exception as err:
        debughere()
        raise err

def columnmapping_vars(columnmapping, indexes=[{'column':'step','type':'int'}]):
    
    orderedmapping = DataTree( (k.name, v.array) for k,v in columnmapping )
    indexecols = getindexes(indexes, orderedmapping)
    
    matlabdata = DataTree(
        data = orderedmapping, 
        columninfo = DataTree( (k.name, k) for k,v in columnmapping ),
        summary = DataTree( (k.name, v.summary) for k,v in columnmapping ),
        indexes = indexecols,
        # "configuration": configuration,
    )
    
    return matlabdata

def columnmapping_matlab(columnmapping, orderedmapping, indexes):
        
    matlabdata = DataTree(
        data = orderedmapping, 
        columninfo = OrderedDict( (k.name, k) for k,v in columnmapping ),
        summary = OrderedDict( (k.name, v.summary) for k,v in columnmapping ),
        indexes = indexes,
        # "configuration": configuration,
    )
    
    return matlabdata

def save_columns_matlab(columnmapping, orderedmapping, configuration, indexes, file):
    with open(str(file),'wb') as outfile:
        print("Writing matlab file...")
        
        matlabdata = columnmapping_matlab(columnmapping, orderedmapping, indexes)
        
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

def load_columns_matlab(filepath, dbg=DebugNone()):
    if dbg:
        print("Reading matlab file: `{}` ...".format(str(filepath)))
        debug(sio.whosmat(str(filepath)))
        print()
    
    # http://stackoverflow.com/questions/6273634/access-array-contents-from-a-mat-file-loaded-using-scipy-io-loadmat-python
    with open(str(filepath),'rb') as file:
        data = DataTree()
        sio.loadmat(file, mdict=data, squeeze_me=True, struct_as_record=False,)
        return data


def save_columns_numpy(columnmapping, orderedmapping, configuration, indexes, file):
    with open(str(file),'wb') as outfile:
        print("Writing numpy file...")
        np.savez_compressed(outfile, data=orderedmapping, columninfo={ k[0].name: k[0] for k in columnmapping }, indexes=indexes, configuration=configuration)

def save_columns_json(columnmapping, orderedmapping, configuration, indexes, file):

    print("Writing json file...")
    json_data = {'data':orderedmapping, 'columninfo':{ k[0].name: k[0] for k in columnmapping }, 'indexes':indexes, 'configuration':configuration}
    Json.write_json_to(file, json_data)
    
def save_columns_json_config(columnmapping, orderedmapping, configuration, indexes, file):

    print("Writing json file...")
    json_data = {'columninfo':{ k[0].name: k[0] for k in columnmapping }, 'indexes':indexes, 'configuration':configuration}
    Json.write_json_to(file, json_data)

def save_columns_pickle(columnmapping, orderedmapping, configuration, indexes, file):
    import pickle
    with open(str(file),'wb') as outfile:
        print("Writing python pickle file...")
        json_data = {'data':orderedmapping, 'columninfo':{ k[0].name: k[0] for k in columnmapping }, 'indexes':indexes, 'configuration':configuration}
        Json.dump_json(json_data)
        

def load_columns_pickle(filepath):
    import pickle
    with open(str(filepath),'rb') as file:
        print("Reading pickle file: `{}` ...".format(str(filepath)))
        return pickle.load(file)

def load_columns_json(filepath):
    return Json.load_json_from(filepath)

# @debugger
def save_columns_excel(columnmapping, orderedmapping, configuration, indexes, file):
    df1 = pd.DataFrame( orderedmapping )
    df2 = pd.DataFrame( [ k[0] for k in columnmapping ] )
    df3 = pd.DataFrame( [ [k]+list(v) for k,v in flatten(indexes,sep=".").items() ] )
    df4 = pd.DataFrame( [ [k, str(v)] for k,v in flatten(configuration,sep=".").items() ] )
    
    with ExcelWriter(str(file)) as writer:
        # [ENH: Better handling of MultiIndex with Excel](https://github.com/pydata/pandas/issues/5254)
        # [Support for Reading Excel Files with Hierarchical Columns Names](https://github.com/pydata/pandas/issues/4468)
        print("Creating excel file...")
        df1.to_excel(writer,'Data', float_format="%12.4f")
        df2.to_excel(writer,'ColumnInfo')
        df3.to_excel(writer,'Indexes')
        df4.to_excel(writer,'Configuration')
        print("Writing excel file...")
        writer.save()

    