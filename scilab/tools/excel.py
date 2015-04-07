## Utils 
import shutil, re, sys, os, itertools, argparse, json, types
import openpyxl
from scilab.tools.project import *


def wsRange(ws, rng):
    def toValue(obj):
        if hasattr(obj,'__iter__'):
            return [ toValue(o) for o in obj]
        else:
            return obj.value if obj.internal_value else None
     
    return toValue(ws[rng])
    
def wsRangeFrom(ws, a, b):
    return wsRange(ws, "{}:{}".format(a,b))
    
def rangerFor(ws):
    return lambda r: wsRange(ws, r)
    
def rangerForRow(ws):
    return lambda r: wsRange(ws, r)[0]
    
def tupleFrom(ws, base, n=2):
    col, row = re.match('([A-Za-z]+)(\d+)', base).groups()
    
    colNext = col[:-1] + chr(ord(col[-1])+(n-1))
    cells = next(ws[col+row:colNext+row])
    ret = tuple( c.value for c in cells )
    return ret
    
def tupleDownFrom(ws, base):
    col, row = re.match('([A-Za-z]+)(\d+)', base).groups()
    rowNext = str(int(row)+1)
    cells = ws.range[col+row:col+rowNext]
    return (cells[0][0].value, cells[1][0].value )
    
def grouper(iterable, n=2, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    if fillvalue:
        return itertools.zip_longest(fillvalue=fillvalue, *args)
    else:
        return zip(*args)

def stripDescrip(desc):
    if desc:
        return desc.rstrip(':').lower().replace('.','').replace(' ','_')

def dictFrom(values):
    # pairs = [ z for z in grouper(values)]
    # debug(pairs)
    data = {}
    
    for a,b in grouper(values):
        # debug(a,b,'\n')
        k = stripDescrip(a)
        data[k] = b
    
    return data

def process_definitions_column(ws, data, col, i,j,stop_key=None, dbg=None, has_units=False):
    for i in range(i,j):
        # debug(col, i,)
        
        if not has_units:
            k, v = tupleFrom(ws, '%s%d'%(col,i),n=2)
        elif has_units:
            ret = tupleFrom(ws, '%s%d'%(col,i),n=3)
            k = ret[0]
            v = valueUnits(*ret[1:])._asdict()
            
        if not k:
            continue
        elif type(k) in  [float, int]:
            continue
        elif stop_key in k or stop_key in k.lower():
            break
        
        # if dbg:
        #     if __name__ != '__main__':
        #         from scilab.tools.project import debug
        #     else:
        #         from Project import debug
        #     debug(k, v, '\n')
        
        data.update( dictFrom((k,v)) )
    
    return i
    
