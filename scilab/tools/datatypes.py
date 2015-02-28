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
        if name in self:
            return self.__getitem__(name)
        else:
            raise AttributeError(self._keyerror(name))
            
    def _keyerror(self, name):
        avail_keys = set(str(s) for s in self.keys())
        return "Key `{}` not found in: {}".format(name,avail_keys)
        
    def __setattr__(self, name, value):
        self[name] = value
        return value
    
    def __getitem__(self, name):
        try:
            if isinstance(name,tuple):
                top = self
                for n in name:
                    if n in top:
                        top = top[n]
                    else:
                        return None
                return top
            else:
                return super().__getitem__(name)
        except KeyError:
            raise KeyError(self._keyerror(name))
    
    def __setitem__(self, name, value):
        """ Set item using default parent method. If a tuple is passed in, a new DataTree will be created if needed. """
        if isinstance(name,tuple):
            try:
                try:
                    if name[0] in self:
                        super().__getitem__(name[0]).__setitem__(name[1:], value)
                    else:
                        top = self
                        for sub in name[:-1]:
                            subdict = DataTree()
                            top[sub] = subdict 
                            top = subdict
                        else:
                            top[name[-1]] = value
                except AttributeError as err:
                    # raise ValueError("unable to create subtree starting at: `{}`".format(name))
                    raise ValueError('', name)
            except ValueError as err:
                raise ValueError("unable to create subtree `{}` from: `{}`".format(name, err.args[-1]),err.args[-1])
        else:
            super().__setitem__(name, value)
    
    def __str__(self):
        return pprint.pformat(self)

    def __iter__(self):
        return sorted(super().__iter__()).__iter__()

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
            # print("d2:",d2.zz)

            assert d1 == {'a': {'aa': 'sublevel'}, 'b': {}, 'c': {'cc': 'sublevel'}} 
            assert d2 == {'a': 3, 'b': {}, 'c': {'cc': 'sublevel'}} 
            
        @test_in(tests)
        def test_datatree_sub3():
    
            # empty sub
            d1 = DataTree()
            print()
            
            d1['a','b','bb'] = 'foo'
            print()

            d1['a','b','c','d'] = 'bar'
            print()

            print('d1:',d1)
            # assert d1 == {'a':{'b':'foobar'}}
            assert d1 == {'a':{'b':{'bb':'foo','c':{'d':'bar'}}}}

        @test_in(tests)
        def test_datatree_sub4():
    
            # empty sub
            d1 = DataTree()
            print()
            
            d1['a','b','c'] = 'foo'
            print()

            try:
                d1['a','b','c','d'] = 'bar'
                raise Error("Previous should result in an error")
            except ValueError:
                pass

            print('d1:',d1)
            
            assert d1 == {'a':{'b':{'c':'foo'}}}
    
        @test_in(tests)
        def test_datatree_sub3():
    
            # empty sub
            d1 = DataTree()
            print()
            
            d1['a','b','bb'] = 'foo'
            print()

            assert d1 == {'a':{'b':{'bb':'foo'}}}
            assert d1['a','b','bb'] == 'foo'
            assert d1['a','b','bb','not','here'] == None
            
        
    