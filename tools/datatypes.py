#!/usr/bin/env python3

from collections import namedtuple
import pprint

try:
    from testingtools import Tests, test_in
except:
    from scilab.tools.testingtools import Tests, test_in

class NamedTuple():
    def set(self, **kw):
        vals = [ kw.get(fld, val) for fld,val in zip(self._fields, self) ]
        return self.__class__(*vals)

# Helpers
class DataTree(dict):
    """Default dictionary where keys can be accessed as attributes and
    new entries recursively default to be this class. This means the following
    code is valid:
    
    >>> mytree = jsontree()
    >>> mytree.something.there = 3
    >>> mytree['something']['there'] == 3
    True
    """
    def __init__(self, *args, **kwdargs):
        if 'defaults' in kwdargs:
            defaults = kwdargs['defaults']
            if not type(defaults) == list:
                defaults = defaults.split() 
            for arg in defaults: 
                kwdargs[arg] = None
        if 'withProperties' in kwdargs:
            defaults = kwdargs.pop('withProperties')
            if not type(defaults) == list:
                defaults = defaults.split() 
            for arg in defaults: 
                kwdargs[arg] = DataTree()
        
        super().__init__(*args, **kwdargs)
        
    def set(self,**kw):
        copy = DataTree(self)
        copy.update(**kw)
        return copy
        
    # def merge(self, other):
    #     def mergerer(d, ):
    #         if isinstance(v, collections.MutableMapping):
    #             for k, v in d.items():
    #                 mergerer(v)
    #     def mergerer(d, parent_key='', sep='_'):
    #         items = []
    #         for k, v in d.items():
    #             new_key = parent_key + sep + str(k) if parent_key else str(k)
    #             if isinstance(v, collections.MutableMapping):
    #                 items.extend(flatten(v, new_key, sep=sep).items())
    #             else:
    #                 items.append((new_key, v))
    #         return collections.OrderedDict(items)
    #     self.update(updated)
        
    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError:
            class getatter(object):
                
                def __init__(self, parent):
                    self.parent = parent
                
                def __setitem__(self, name, value):
                    debug(name, value)
                
                
            return getatter(self)
            # raise AttributeError(self._keyerror(name))
            
    def _keyerror(self, name):
        avail_keys = set(str(s) for s in self.keys())
        return "Key `{}` not found in: {}".format(name,avail_keys)
        
    def __getitem__(self, name):
        try:
            return super().__getitem__(name)
        except KeyError:
            raise KeyError(self._keyerror(name))
    
    def __setattr__(self, name, value):
        self[name] = value
        return value
    
    def __str__(self):
        return pprint.pformat(self)

    def __iter__(self):
        return sort(super().__iter__())

class DebugData(DataTree):

    def __bool__(self):
        return True
    
class DebugNone(DebugData):

    def __bool__(self):
        return False
    

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


if __name__ == '__main__':

    with Tests(quiet=False, ) as tests:
    
        foobar = []
    
        @test_in(tests)
        def test_datatree():
            # creationg
            d1 = DataTree()
    
            # simple assigning
            d1.a = 1
            d1['b'] = 2
    
            # sub level with another tree
            d1.c = DataTree(cc="sublevel")
    
            d1['a'] = DataTree(aa="sublevel")
            d1.b = {}
    
            # update from another datatree
            d2 = DataTree()
            d2.update(d1)
            d2.a = 3
    
            print("d1:",d1)
            print("d2:",d2)

    
        @test_in(tests)
        def test_datatree_sub():
    
            # empty sub
            d1 = DataTree()
            d1.a.b = 'foobar'

            print('d1:',d1)

