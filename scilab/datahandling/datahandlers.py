#!/usr/bin/env python3

import os, sys, pathlib, re
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

def getproperty(json_object):
    return next(json_object.values().__iter__())

def getproperties(json_array):
    return [ getproperty(item) for item in json_array ]


def clean(s):
    return s.replace("·",".")


def getfilenames(testfolder, stage, version, matlab=True, excel=True):
    
    filename = testfolder.datacalc / '{stage} | v{ver}.txt'.format(stage=stage, ver=version)
    
    filenames = DataTree()
    filenames.stage = stage
    filenames.version = version
    if matlab: filenames['names','matlab'] = filename.with_suffix('.mat')
    if excel: filenames['names','excel'] = filename.with_suffix('.xlsx')

    return filenames
    
def save_columns(testfolder, name, columnmapping, filenames):
    
    orderedmapping = OrderedDict( (k.name, v.array) for k,v in columnmapping ) 
    
    if 'matlab' in filenames.names:
        save_columns_matlab(columnmapping, orderedmapping, filenames.names.matlab)
    if 'excel' in filenames.names:
        save_columns_matlab(columnmapping, orderedmapping, filenames.names.excel)
        outputs.excel = file

def save_columns_matlab(columnmapping, orderedmapping, file):
    with open(str(file),'wb') as outfile:
        print("Writing matlab file...")
        sio.savemat(outfile, {"data":orderedmapping, "columns": { k[0].name: k[0] for k in columnmapping } } , 
                    appendmat=False, 
                    format='5',
                    long_field_names=False, 
                    do_compression=True,
                    )

def save_columns_excel(columnmapping, orderedmapping, file):
    with ExcelWriter(str(file)) as writer:
        # [ENH: Better handling of MultiIndex with Excel](https://github.com/pydata/pandas/issues/5254)
        # [Support for Reading Excel Files with Hierarchical Columns Names](https://github.com/pydata/pandas/issues/4468)
        print("Creating excel file...")
        df1 = pd.DataFrame( orderedmapping )
        df2 = pd.DataFrame( [ k[0] for k in columnmapping ] )
        df1.to_excel(writer,'Data')
        df2.to_excel(writer,'ColumnInfo')
        print("Writing excel file...")
        writer.save()

    