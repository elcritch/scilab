#!/usr/local/bin/python3

import argparse, re, os, glob, sys, collections
import itertools, inspect, logging, pathlib 

Path = pathlib.Path
os = os
sys = sys
re = re
logging = logging

if __name__ == '__main__':
    import os, sys, pathlib
    sys.path.insert(0,[ str(p) for p in pathlib.Path('.').resolve().parents if (p/'scilab').exists() ][0] )

import scilab.tools.testingtools as testingtools
import scilab.tools.datatypes as datatypes
from scilab.tools.datatypes import *
from scilab.tools.tables import *
from scilab.tools.testingtools import Tests, test_in

Testing = testingtools
collections = collections

class InstronColumnSummary(DataTree):
    pass

class InstronColumnBalance(DataTree):
    pass

class ColumnInfo(namedtuple('_ColumnInfo', 'name label details units full idx'), NamedTuple):
    pass

class InstronColumnData(namedtuple('_InstronColumnData', 'array summary name label details units full idx'), NamedTuple):
    pass

def todatatree(item,depth=0):
    """convert json to data tree ... """
    if isinstance(item, collections.Mapping):
        print("'.'*depth, todatatree: dict:",len(item))
        output = DataTree()
        for key,value in item.items():
            print('.'*depth, "todatatree: dict:key:",key)
            output[key] = todatatree(value,depth+1)
        return output
    elif isinstance(item, collections.Sequence):
        print('.'*depth, "todatatree:list:",len(item))
        output = [ todatatree(i,depth+1) for i in item ]
    else:
        print('.'*depth, "todatatree:item",str(type(item)).replace('<','≤'))
        return item


def debugger_summary(idx, val, prefix='_', depth=0):
    msg = "{}+ [{}]<{}>: ".format(prefix*depth, idx, str(type(val)))
    # print('debugger_summary:',str(type(val)).replace('<','≤').replace('>','≥'))
    if 'ndarray' == val.__class__.__name__:
        return msg + "ndarray: "+str(val.shape)
    elif hasattr(val, '__summary__'):
        return msg + val.__summary__()
    elif isinstance(val, dict):
        # print('items:', flush=True, file=sys.stderr)
        ignore = getattr(val, '_ignore', [] )
        print('debugger_summary:ignore:'+str(ignore))
        for k,v in flatten(val, sep='.').items():
            if any([i in k for i in ignore]):
                # msg += '\nignored key: {} type:{}'.format(k,type(v))
                continue
            msg += '\n' + debugger_summary(k, v, depth=depth+1)
        return msg
    else:
        return msg+str(val)

def debugger(func, debug=False):
    """ Use to annotate functions for debugging purposes. """
    pd = lambda *a, **kw: print(*a, end=' ', flush=True, file=sys.stderr, **kw)
    pdln = lambda *a, **kw: print(*a, flush=True, file=sys.stderr, **kw)
    
    # np.set_printoptions(threshold=10)
    def debugger_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as err:
            args = itertools.chain( enumerate(args), kwargs.items())
            # args = [ "{}-> {}".format(k, str(v)) for k,v in args ]
            print("Trace:", func.__name__,' Args :=\n+ ', flush=True,file=sys.stderr)
            
            for idx, arg in args:
                print('+ [{}]<{}>'.format(idx, type(arg)), end=' ', flush=True, file=sys.stderr)
                if hasattr(arg, '_asdict'):
                     arg = vars(arg)
                print(debugger_summary(idx, arg), flush=True, file=sys.stderr)
            
            raise err
            
    return debugger_wrapper    

def bindMethod(cls, name, func):
    """ Dynamically bind a new method to a class. """
    from types import MethodType
    setattr(cls, name, MethodType(func, cls))

def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)
    
def attributesAccessor(node, path):
    try:
        if type(path) is str:
            path = path.split('.')
        for key in path:
            key = int(c) if key.isnumeric() else key
            node = node[key]
        return node
    except KeyError:
        return 'n/a'

USER_HOME = Path(os.path.expanduser('~'))

def debug(*args, end='\n',fmt='{} ',sep='->', file=None):
    try:
        st = inspect.stack()[1]
        funcName = st[3]
        funcCallStr = st[4]

        varnames = re.search('debug\((.*)\)', funcCallStr[0])
        varnames = varnames.groups()[0].split(',')

        def fmt_v_str(v):
            if isinstance(v, Path) and str(v).startswith(str(USER_HOME)):
                vstr = '~/'+str(v.relative_to(USER_HOME))
            else:
                vstr = str(v)
            if '<' in vstr:
                vstr = vstr.replace('<','&lt;')
            if '>' in vstr:
                vstr = vstr.replace('>','&gt;')
            
            return "`%s`"%vstr if vstr.count('\n') == 0 else '\n'+vstr.replace('\n', '\n> ....')

        for n, v in zip(varnames, args):
            if isinstance(v, dict):
                print(fmt.format(n.strip()), '::->', end=end, file=file)
                for i,j in flatten(v,sep='.').items():
                    print('.... ', fmt.format(i.strip()), sep, fmt_v_str(j), end=end, file=file)
                # print( json.dumps(v, indent='    ').replace('    ','....'), end=end, file=file)
            else:
                print(fmt.format(n.strip())+sep, fmt_v_str(v), end=end, file=file)
        
    except Exception as err:
        raise err
        print('debug(...error...)')


if __name__ == '__main__':

    with Tests(quiet=False, ) as tests:
    
        foobar = []
    
        @test_in(tests)
        def test_debug():
            """ test debug """
            foobar = [1,2,3]
            foolist = ["a","b"]

            debug(foobar, foolist)
            debug(foobar, foolist, end='\n', fmt='{}', sep=':=')

        @test_in(tests)
        def test_bindMethod():
            """ bind method for adding a method to a class/instance dynamically """

            def foo(self):
                print("foo", self)

            class C(object): 
                pass 

            c1 = C()
            assert hasattr(c1, 'method') == False

            bindMethod(C, 'method', foo)

            assert hasattr(c1, 'method') == True

        @test_in(tests)
        def test_grouper():
            """groups sequences into groups grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"""    
            # grouper
            ans = [ a for a in grouper(3, 'ABCDEFG', 'x') ]
            debug(ans, )
            assert ans == [('A', 'B', 'C'), ('D', 'E', 'F'), ('G', 'x', 'x')]
             # "ABC DEF Gxx"

            ans1 = [ g for g in grouper(1, 'one two three'.split())]
            debug(ans1)
            ans2 = [ g for g in grouper(2, 'one two three'.split())]
            debug(ans2)

