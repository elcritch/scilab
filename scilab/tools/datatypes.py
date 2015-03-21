#!/usr/bin/env python3

from collections import namedtuple
import pprint, collections, numbers, itertools

try:
    from testingtools import Tests, test_in
except:
    from scilab.tools.testingtools import Tests, test_in

class NamedTuple():
    def set(self, **kw):
        vals = [ kw.get(fld, val) for fld,val in zip(self._fields, self) ]
        return self.__class__(*vals)


    
def hasshape(mapping, *args):
    keys = set(mapping.keys())
    shape = set(args)
    return keys.union(shape) == shape # Is there a better way?

def isshape(mapping, *args):
    keys = set(mapping.keys())
    return keys == set(args)

valueIndex=namedtuple("valueIndex", ["value","idx"])
valueIndexUnits=namedtuple("valueIndexUnits", ["value","idx", "units"])
valueUnitsStd=namedtuple("valueUnitsStd", ["value","units","stdev"])
valueUnits=namedtuple("valueUnits", ["value","units"])
linearFit=namedtuple("linearFit", ["slope","intercept"])

Shapes = collections.OrderedDict(
    valueIndex=["value","idx"],
    valueIndexUnits=["value","idx", "units"],
    valueUnitsStd=["value","units","stdev"],
    valueUnits=["value","units"],
    linearFit=["slope","intercept"],
    )

def shapeof(v):
    if isinstance(v, collections.Mapping):
        for shape, fields in Shapes.items():
            if isshape(v, *fields):
                return ("mapping", shape, fields, )
        else:
            return ("mapping", "", [])
    elif isinstance(v, tuple) and hasattr(v, "_fields"):
        for shape, fields in Shapes.items():
            if isshape(v._asdict(), *fields):
                return ("namedtuple", shape, fields, )
        else:
            return ("namedtuple", "", [])
    elif isinstance(v, (list, tuple)):
        return ("list", "items", [])
    elif isinstance(v, (numbers.Number)):
        return ("number", "int" if isinstance(v, (int,)) else "float", [])
    elif isinstance(v, (str)):
        return ("string", "value", [])
    else:
        return ("", "", [])
        
        
class OrderedUserDict:
    def __init__(self, dict=None, **kwargs):
        self.__dict__['__ordereddict__'] = collections.OrderedDict()
        if dict is not None:
            self.update(dict)
        if len(kwargs):
            self.update(kwargs)
    def __repr__(self): return dict.__repr__(self.__ordereddict__)
    def __cmp__(self, other):
        if isinstance(other, OrderedUserDict):
            print("cmp:", other)
            return cmp(self.__ordereddict__, other.data)
        else:
            print("cmp:", other)
            return cmp(self.__ordereddict__, other)
    def __eq__(self, other):
        if other is None:
            pass
        elif isinstance(other, OrderedUserDict):
            print("eq:orderd:", other)
            return self.__ordereddict__ == other.__ordereddict__
        elif isinstance(other, type({})) or not hasattr(other, 'items'):
            print("eq:dict:", other, )
            return self.__ordereddict__ == other
    def __len__(self): return len(self.__ordereddict__)
    def __getitem__(self, key):
        if key in self.__ordereddict__:
            return self.__ordereddict__[key]
        if hasattr(self.__class__, "__missing__"):
            return self.__class__.__missing__(self, key)
        raise KeyError(key)
    def __setitem__(self, key, item): self.__ordereddict__[key] = item
    def __delitem__(self, key): del self.__ordereddict__[key]
    def clear(self): self.__ordereddict__.clear()
    def copy(self):
        if self.__class__ is OrderedUserDict:
            return OrderedUserDict(self.__ordereddict__.copy())
        import copy
        data = self.__ordereddict__
        try:
            self.__ordereddict__ = {}
            c = copy.copy(self)
        finally:
            self.__ordereddict__ = data
        c.update(self)
        return c
    def keys(self): return self.__ordereddict__.keys()
    def items(self): return self.__ordereddict__.items()
    def iteritems(self): return self.__ordereddict__.iteritems()
    def iterkeys(self): return self.__ordereddict__.iterkeys()
    def itervalues(self): return self.__ordereddict__.itervalues()
    def values(self): return self.__ordereddict__.values()
    def has_key(self, key): return key in self.__ordereddict__
    def update(self, d=None, **kwargs):
        if d is None:
            pass
        elif isinstance(d, OrderedUserDict):
            self.__ordereddict__.update(d.__ordereddict__)
        elif isinstance(d, type({})) or not hasattr(d, 'items'):
            self.__ordereddict__.update(d)
        else:
            for k, v in d.items():
                self[k] = v
        if len(kwargs):
            self.__ordereddict__.update(kwargs)
    def get(self, key, failobj=None):
        if key not in self:
            return failobj
        return self[key]
    def setdefault(self, key, failobj=None):
        if key not in self:
            self[key] = failobj
        return self[key]
    def pop(self, key, *args):
        return self.__ordereddict__.pop(key, *args)
    def popitem(self):
        return self.__ordereddict__.popitem()
    def __contains__(self, key):
        return key in self.__ordereddict__
    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

class IterableOrderedUserDict(OrderedUserDict):
    def __iter__(self):
        return iter(self.__ordereddict__)

# Helpers
class DataTree(OrderedUserDict, dict):
    """Default dictionary where keys can be accessed as attributes and
    new entries recursively default to be this class. This means the following
    code is valid:
    
    >>> mytree = jsontree()
    >>> mytree.something.there = 3
    >>> mytree['something']['there'] == 3
    True
    """
    def __init__(self, *args, **kwdargs):
        OrderedUserDict.__init__(self, *args, **kwdargs)
        
        # self.__dict__['__ordereddict__'] = collections.OrderedDict(*args, **kwdargs)
        
    def set(self,**kw):
        copy = DataTree(self)
        copy.update(**kw)
        return copy
        
    def __add__(self, other):
        return self.set(**other)
        
    def __sub__(self, other):
        return DataTree( (k,v) for k,v in self.items() if k not in other )
        

    def __getattr__(self, name):
        if name in self:
            return self.__getitem__(name)
        else:
            raise AttributeError(self._keyerror(name))
            
    def _keyerror(self, name):
        avail_keys = set(str(s) for s in self.keys())
        return "Key `{}` not found in: {}".format(name,avail_keys)
    
    def has_key(self, key): 
        return key in self.__ordereddict__
        
    def __setattr__(self, name, value):
        # self[name] = value
        
        self.__ordereddict__[name] = value
            
        return value
    
    def __getitem__(self, name):
        try:
            if isinstance(name,(tuple, list)):
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
                    if name[0] in self.__ordereddict__:
                        super().__getitem__(name[0]).__setitem__(name[1:], value)
                    else:
                        top = self.__ordereddict__
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
            
            # Maintain Insert Order
            self.__ordereddict__[name] = value
            # self..__setitem__(name, value)
    

    def astuples(self):
        return flatten(self, astuple=True, sort=True)
            

def mapd(d, valuef=(lambda k, v: v), keyf=(lambda k,v: k) ):
    return DataTree({ keyf(k,v): valuef(k,v) for k,v in d.items() })

def mapl(*args, **kwargs):
    return list(map(*args, **kwargs))

def consd(*dicts):
    return DataTree( itertools.chain.from_iterable(d.iteritems() for d in args) )

def flatd(d):
    return list( (k,v) for k,v in d.items())

def pruned(d, *args):
    dn = d.copy()
    for a in args:
        dn.pop()
    return dn

def unpack(d, *args):
    return tuple( d[i] for i in args)

def flatten(d, parent_key='', sep='.', func=None, ignore=[], astuple=False, sort=True, tolist=False, dolist=False):
    if not isinstance(d, collections.MutableMapping):
        return d
    
    items = []
    
    # if tolist:   astuple = True
    if astuple:  func = lambda p,ks: tuple(p)+(ks,)
    if not func: func = lambda p,ks: (p + sep + ks if p else ks)
        
    for k, v in d.items():
        ks = str(k)
        if ks in ignore:
            continue
        
        new_key = func(parent_key, ks) 
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep, func=func, ignore=ignore).items())
        elif dolist and isinstance(v, list):
            dv = collections.OrderedDict(enumerate(v))
            items.extend(flatten( dv, new_key, sep=sep, func=func, ignore=ignore).items())
        else:
            items.append((new_key, v))
    
    sorter = sorted if sort else (lambda x: x)
    items = sorter(items,key=lambda x: x[0])
    if tolist:
        return items
    else:
        return collections.OrderedDict(items) 

def flatten_type(d, ignore=['__builtins__', 'summaries']):
    kenv = sorted((k,str(type(v)).replace('<','')) for k,v in flatten(d,sep='.',ignore=ignore).items() if not 'summaries' in k)
    return collections.OrderedDict(kenv)


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
            print("d1:",d1.__dict__)
            print("d2:",d2)
            # print("d2:",d2.zz)

            assert {'a': {'aa': 'sublevel'}, 'b': {}, 'c': {'cc': 'sublevel'}} == d1
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
            
            name = "c"
            d1[name] = DataTree()
            d1[name].subc = True
            
            d1['a','b','bb'] = 'foo'
            print("d1:",d1)
            print()

            assert d1 == {'a':{'b':{'bb':'foo'}}, 'c':{'subc':True}}
            assert d1['a','b','bb'] == 'foo'
            assert d1['a','b','bb','not','here'] == None
            
        @test_in(tests)
        def test_flatten():
            
            d1 = DataTree()
            print()
            
            d1['c','subc'] = True            
            d1['a','b','bb'] = 'foo'
            
            print(d1)
            
            fd1 = flatten(d1,sep='_')
            print("fd1",fd1)
            assert fd1 == {'a_b_bb':'foo', 'c_subc':True}
            
            fd2 = flatten(d1, astuple=True)
            
            print(fd2)
            assert fd2 == { ('a','b','bb'): 'foo', ('c','subc'):True }
            
        @test_in(tests)
        def test_iters():
            
            d1 = DataTree()
            print()

            d1.a = 'alpha'
            d1.z = 'zeta'
            d1['c','ca'] = 'foo1'
            d1['c','cc'] = 'foo2'
            d1['b','ac'] = 'bar2'
            d1['b','ab'] = 'bar3'
            
            print("d1:",d1)
            print("d1.keys",d1.keys())
            print("d1.items",d1.items())
            print("d1.__ordereddict__",d1.__ordereddict__)
            
