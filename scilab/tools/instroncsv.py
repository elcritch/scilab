#!/usr/bin/env python3

import codecs, encodings, pprint
import numpy as np

import collections, itertools, logging
from collections import OrderedDict, namedtuple

from scilab.tools.project import *
from scilab.utilities.normalize_data import *


class NamedTuple():
    def set(self, **kw):
        vals = [ kw.get(fld, val) for fld,val in zip(self._fields, self) ]
        return self.__class__(*vals)
    # def __str__(self):
    #     return "{}({})".format(self.__class__.__name__, repr(self))

def InstronColumnData__call__(self):
    return self.array

InstronColumnData.__call__ = InstronColumnData__call__

def camelCase(name, capitalizeFirst=False, removeCommon=[]):
    words = [ w for w in name.split() if w.lower() not in removeCommon ]
    name = ''.join( ""+w[:1].upper()+w[1:].lower() for w in words )
    name = ""+(name[:1].lower() if not capitalizeFirst else name[:1].upper())+name[1:]
    return name

def getcolumninfo(idx, column, longname=True):
    
    column = str(column)
    
    # Split name based on parens. 
    parts = column.replace(')','').split('(')
    label, kind, units = parts[0], '', ''

    # Camel Case Titles 
    name = camelCase(label)
    
    # hack, instron appears to put units last with preceding space
    # two parts, *with* preceding => name & units 
    if len(parts) == 2 and parts[0].endswith(' '): 
        units = parts[1]
    # two parts, no preceding => name & kind
    elif len(parts) == 2:
        kind = parts[1]
    # three parts => name, kind, units
    elif len(parts) == 3:
        kind, units = parts[1:]

    # default to using unique name...
    extraDetails = ' '.join(kind.split("|"))
    uniqueName = name+camelCase(extraDetails, capitalizeFirst=True, )

    columnData = ColumnInfo(
        name=uniqueName if longname else name, 
        label=label, 
        details=kind, 
        units=units, 
        full=column,
        idx=idx,
        )
        
    # debug(columnData)
    return columnData

def getColumnData(headerLine):
    headers = [ h.strip('"').replace(':', '|') for h in headerLine.split(',') ]
    
    # print("Headers:\n\t")
    allColumns = OrderedDict()
    columns = []

    ## Make Columns
    for idx, column in enumerate(headers):
        columnData = getcolumninfo(idx, column, longname=False)
        print('IDX:',idx, columnData.idx)
        columns.append(columnData)
    
    # Handle issue when column names are not unique, such as totalCycleCount
    # Basically, we just take the extra details (Rotary Wavefrom) and camel    
    for column in columns:
        if not column.name:
            logging.warning("Passing:"+str(column))
        elif column.name not in set( [v.name for v in allColumns.values()] + [k for k in allColumns.keys()]) :
            allColumns[column.name] = column
        else:
            
            def makeUnique(c):
                uniqueCol = getcolumninfo(c.idx, c.full, longname=True)

                # logging.warning("Duplicate column name found, making unique column name: "+str(uniqueCol))
            
                debug(uniqueCol)
                # print("assert failed: %s already in %s"%(uniqueCol.name, [ k for k in allColumns.keys()] ))
                
                assert uniqueCol.name not in allColumns.keys() # and not \
                    # print("assert failed: %s already in %s"%(uniqueCol.name, [ k for k in allColumns.keys()] ))
            
                return uniqueCol

            uniqueCol = makeUnique(column).set(idx=column.idx)
            allColumns[uniqueCol.name] = uniqueCol
            
            if allColumns[column.name].name == column.name:
                prevcol = allColumns.pop(column.name)
                uniqueColPrev = makeUnique(prevcol).set(idx=prevcol)
                allColumns[uniqueColPrev.name] = uniqueColPrev
            
            
    return [ v for c, v in allColumns.items() if v ]


# InstronMatrixData = namedtuple('InstronMatrixData', '')
# InstronField = namedtuple('InstronMatrixData', '')
def get_index_slices(data, keyer=None):
    """ Return an array of numpy slices for indexing arrays according to changes in the numpy array `data` """
    indices = (np.where(data[:-1] != data[1:])[0]).astype(int)
    indices_begin = [0] + [ i for i in (indices + 1)] # offset by 1 to get beginning of slices
    indices_end = [ i for i in (indices + 1)]+[-1]
    keyer = keyer or (lambda k: k)
    # debug(indices_begin, indices_end)

    return collections.OrderedDict( (keyer(data[i]), np.s_[i:j:1]) for i,j in zip(indices_begin, indices_end) )
    
class InstronMatrixData(DataTree):
    def __init__(self, *args, **kwdargs):
        super().__init__(*args, **kwdargs)
        self.__dict__['__slices'] = {}
        self.__dict__['indices'] = None

    def getIndices(self, **kwdargs):
        """ return numpy array for slice """
        assert len(kwdargs) == 1
        key, index = kwdargs.popitem()
        indicies = self._getslices(key)[index]
        return indicies
        
    def _getslices(self, keyColumn='step', keyer=lambda x: "step_{:.0f}".format(x)):
        """ Lazy loading of slices based on 'step' column. """
        if keyColumn not in self.__slices:
            npslices = get_index_slices(self[keyColumn].array, keyer=keyer)
            self.__dict__['__slices'][keyColumn] = npslices
        
        return self.__slices[keyColumn]
        
    # def slice(self, **kwdargs):
    #     """ return numpy array for slice """
    #     assert len(kwdargs) == 1
    #     key, index = kwdargs.popitem()
    #     indicies = self._getslices(key)[index]
    #
    #     return InstronMatrixDataSlice(indicies, self)

    def _setIndices(self, indicies):
        self.__dict__['indicies'] = indicies
        return self
    
        
class InstronMatrixDataSlice(object):
    
    def __init__(self, npslice, parent):
        self.npslice = npslice
        self.parent = parent
    
    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            # debug(self.parent[name])
            return self.parent[name][self.npslice]


import time

def csvread(fileName):
    
    
    with open(str(fileName), 'rb') as fileObject:
        t0 = time.time()
        # this must be done to properly read the instron generated csv file which is iso-8859-1 encoded
        # it appears to be a numpy bug in np.genfromtxt that doesn't allow/follow different codecs
        fileObjTranscode = codecs.EncodedFile(fileObject, data_encoding='iso8859_1', file_encoding='iso8859_1')        
        headerLine = fileObjTranscode.readline().decode('iso-8859-1')
        columns = getColumnData(headerLine)
        
        # debug(columns)
        # read matrix data as np matrix... :) 
        matrix = np.genfromtxt(fileObjTranscode, delimiter=',',skip_header=0,filling_values=np.nan,autostrip=True)
        
        data = InstronMatrixData()
        data.__dict__['_matrix'] = matrix
        
        for (idx, cd) in enumerate(columns):
            # debug(idx, cd.name, cd)
            # print()
            xx = matrix[:,idx]
            summary = InstronColumnSummary(mean=xx.mean(),std=xx.std(),mins=getmin(xx),maxs=getmax(xx))
            data[cd.name] = InstronColumnData(xx, summary, *cd)
        
        # for idx in step_indices:
            # debug(idx, step[idx], step[idx-1])
        
        t1 = time.time()
        
        logging.warn("csvread took %.2f seconds"%(t1-t0))
        return data


if __name__ == '__main__':
    fileName = RAWDATA+"/NTM-MF-PRE (test4, trans, uts)/09sep16.1-x3-3/09sep16.1-x3-3.steps.tracking.csv"
    # fileName = "InstronCSV.test.csv"
    # TODO: fix to use this file
    
    print("Testing...\n----------------------")
    m = csvread(fileName)
    
    debug(m.keys())
    
    debug(m.position)
    
    print("Instron data object:\n", m )

    print("\n\n# Matrix:")
    
    print( ','.join([ "%s"%n for n in m._matrix[0,:] ]) )
    print( ','.join([ "%s"%n for n in m._matrix[1,:] ]) )

    time_slice = m.slice(step=0).totalTime
    print('time_slice',time_slice, "...", len(time_slice),'\n\n')
    
    step0 = m.getIndices(step=0)
    print("step slice repr:", repr(step0))
    step_slice1 = set(m.step.array[step0])
    debug(step_slice1)
    step_slice2 = set(m.step.array[m.getIndices(step=1)])
    debug(step_slice2)
    
    
    print("\n# Raw file: ")
    with open(fileName, 'rb') as fileObject:
        # this must be done to properly read the instron generated csv file which is iso-8859-1 encoded
        # it appears to be a numpy bug in np.genfromtxt that doesn't allow/follow different codecs
        fileObjTranscode = codecs.EncodedFile(fileObject, data_encoding='iso8859_1', file_encoding='iso8859_1')     
        
        print(0, fileObjTranscode.readline())
        print(1, fileObjTranscode.readline())
        print(2, fileObjTranscode.readline())
        print(3, fileObjTranscode.readline())
        print(4, fileObjTranscode.readline())
    
    
    
    
    