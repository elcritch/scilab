#!/usr/local/bin/python3

import argparse, re, os, glob, sys, collections, inspect, json
import itertools, inspect, logging, pathlib , urllib

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
import tabulate 

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

class CustomDebugJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, Path):
                return str(obj)
            elif isinstance(obj, tuple) and hasattr(obj, '_fields'):
                return vars(obj)
            elif isinstance(obj, slice):
                return (obj.start, obj.step, obj.stop)
            else:
                # return super().default(obj)
                return json.JSONEncoder.default(self, obj)
                
        except TypeError as err:
            # print("Json TypeError:"+str(type(obj))+" obj: "+str(obj))
            return { '_type_': str(type(obj)), '_value_': repr(obj) }

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

def catcher(func, *args, **kwargs):
    try:
        return func(*args, **kwargs), None
    except Exception as err:
        return '', err    

def debughere(msg=None, ignores=[]):
    
    ignores += ['self']
    stack = list(reversed(inspect.stack()))
    f_locals = [ s[0].f_locals for s in stack ]
    f_names = ' -> '.join( "{}:{}".format(s[3],s[0].f_lineno) for s in stack )
    print(debugger_summary(f_names, f_locals[-2], ignores=ignores))

    if msg:
        raise Exception(msg)

def debugconsole(err):
    st = inspect.stack()    

    def formatstack(currst):
        return ""
    
    print("<em>Script: Debug Console</em>")
    print("""__CONSOLE__::
    <script type="text/javascript">
    
        console.log('debug python: %s as json: \n%O', "{name}", {{"pyobject": {json} }});
        
    </script>
    """.format(name="traceback", json=json.dumps(tb_dict,cls=CustomDebugJsonEncoder)).replace("\n",""))

def safefmt(strval, *args, **kwargs):
    retval, reterr = catcher( lambda: strval.format(*args, **kwargs) )
    
    if reterr:
        funcs = '.'.join( f[3] for f in reversed(inspect.stack()) )
        args_d = { i:a for i,a in enumerate(args) }
        args_d and print(debugger_summary(funcs, args_d, ignores=['filestructure.projdesc',]))
        kwargs and print(debugger_summary(funcs, kwargs, ignores=['filestructure.projdesc',]))
        # kwargs_json = json.dumps(kwargs, cls=CustomDebugJsonEncoder)
        
        # print(" <em>Script:</em> ")
        # print("""__CONSOLE__::
        # <script type="text/javascript">
        #
        #     console.log('debug python: %s as json: \n%O', "{name}", {{"pyobject": {json} }});
        #
        # </script>
        # """.format(name="traceback", json=json.dumps(tb_dict,cls=CustomDebugJsonEncoder)).replace("\n",""))
        #
        #
        #
        # print(" <em>Script:</em> ")
        # print("""__CONSOLE__::
        # <script type="text/javascript">
        #
        #     console.log('debug python: %s as json: \n%O', "{name}", {{"pyobject": {json} }});
        #
        # </script>
        # """.format(name="kwargs", json=kwargs_json).replace("\n",""))
        
        raise Exception("Error formatting string: {}".format(strval), reterr)
    
    return retval
    
class Empty(object):

    def __call__(self, *args, **kwargs):
        return self
        
    def __bool__(self):
        return False
        
    def __getattr__(self, name):
        return self


def debugger_str(val, tablefmt="pipe", ignores=[], end=''):
    if 'ndarray' == val.__class__.__name__:
        return "ndarray: "+str(val.shape)
    elif hasattr(val, '__summary__'):
        return val.__summary__()
    elif isinstance(val, dict):
        rows = [ (k, debugger_str(v)) for k,v in flatten(val, sep='.').items() if not any(i in k for i in ignores) ]
        tbstr = str( tabulate.tabulate( rows, headers=['Key', 'Value'], tablefmt=tablefmt ) ).strip()
        
        if end != '\n':
            return tbstr.replace('\n',end)
        else:
            return tbstr
    else:
        return repr(val)
    
    
def debugger_summary(idx, val, prefix='', depth=0, fmt="<h1>Debug:<b>{idx}</b>:</h1> {val})</1>", ifmt="\n{}", tablefmt="html", ignores=[]):
    msg = fmt.format(pre=prefix*depth, idx=idx, val=str(type(val)).replace('<','≤').replace('>','≥'))
    
    return msg + ifmt.format(debugger_str(val, tablefmt=tablefmt, ignores=ignores))

def debugfile(file, debug=False):
    try:
        # print("<a src='file://{file}'>{file.name}</a>".format(file=Path(str(file))))
        print("file://{file}".format(file=urllib.parse.quote(str(file))))
    except Exception as err:
        print(str(file))

def debugger(func, debug=False):
    """ Use to annotate functions for debugging purposes. """
    
    def display(msg, *args, flush=True, file=sys.stderr, end='', sep=' ', **kwargs):
        print(msg.format(*args, **kwargs).strip(), flush=True, file=sys.stderr, end=end, sep=sep)
        # with open('/tmp/1','a') as fl1: fl1.write(msg.format(*args, **kwargs)+end)
        
    # np.set_printoptions(threshold=10)
    def debugger_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as err:
            args = itertools.chain( enumerate(args), kwargs.items())
            # args = [ "{}-> {}".format(k, str(v)) for k,v in args ]
            display("<h2>Trace: Func `{}`</h2>\n Args := \n <ol>", func.__name__)
            
            for idx, arg in args:
                display('<li> [{idx}]({tp}) </li> '.format(idx=idx, tp=type(arg)) )
                if hasattr(arg, '_asdict'):
                     arg = vars(arg)
                display("<ul>{}</ul>", debugger_summary(idx, arg, fmt="<li> <u>{idx}:</u> {val} </li>").strip(), ifmt="{}")
            
            display("</ol>")
            
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

