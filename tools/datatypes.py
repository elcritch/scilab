#!/usr/bin/env python3

from collections import namedtuple

class NamedTuple():
    def set(self, **kw):
        vals = [ kw.get(fld, val) for fld,val in zip(self._fields, self) ]
        return self.__class__(*vals)

class InstronColumnSummary(DataTree):
    pass

class InstronColumnBalance(DataTree):
    pass

class InstronColumnData(namedtuple('_InstronColumnData', 'array name label details units idx summary'), NamedTuple):
    pass

def unwrap_array(func):
    def unwrap(data, *args, **kwargs):
        if 'array' in data:
            return func(data.array, *args, **kwargs)
        else:
            return func(data, *args, **kwargs)
    unwrap.__name__ = func.__name__
    return unwrap

def sliced_array(func):
    def sliced(array, sl, *args, **kwargs):
        return func(array[sl], *args, **kwargs)
    sliced.__name__ = func.__name__
    return sliced
