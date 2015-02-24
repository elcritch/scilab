#!/usr/local/bin/python3

import argparse, re, os, glob, sys, pprint, itertools, json
import inspect
import logging
from pathlib import Path

import collections
from collections import OrderedDict, namedtuple

from types import MethodType

def stems(file):
    return file.name.rstrip(''.join(file.suffixes))

Path.stems = stems

def flatten(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + str(k) if parent_key else str(k)
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def debugger_summary(idx, val, prefix='_', depth=0):
    msg = "{}+ [{}]<{}>: ".format(prefix*depth, idx, str(type(val)))
    if 'ndarray' in val.__class__.__name__:
        return msg + "ndarry[shape={}]".format(shape=val.shape)         
    elif isinstance(val, dict):
        print('items:', flush=True, file=sys.stderr)
        
        for k,v in flatten(val, sep='.').items():
            msg += '\n' + debugger_summary(k, v, depth=depth+1)
        return msg
    else:
        return msg+repr(val)

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


# from addict import Dict

from inspect import isgenerator

# Helpers
# class DataTree(collections.OrderedDict):
# class DataTree(collections.defaultdict):
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
        
    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError:
            raise AttributeError(self._keyerror(name))
            
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


class DebugData(DataTree):

    def __bool__(self):
        return True
    
class DebugNone(DebugData):

    def __bool__(self):
        return False
    

def ResearchDir(project_setup_file="project-setup.sh"):
    abspath = os.path.abspath(".").split(os.sep)

    def find(dirs):
        if not dirs:
            logging.warn("Could not find project dir")
            return ''
        elif os.path.exists(os.sep.join(dirs)+os.sep+project_setup_file):
            return os.sep.join(dirs)
        else:
            return find(dirs[:-1])
        
    RESEARCH = find(abspath)
    RAWDATA = os.sep.join((RESEARCH, "07_Results", "02_Raw"))

    return (RESEARCH, RAWDATA)

if not 'RESEARCH' in globals().keys() or not 'RAWDATA' in globals().keys():
    global RESEARCH, RAWDATA
    RESEARCH, RAWDATA = ResearchDir()
    
print ("Research (Project) Directory:", RESEARCH, RAWDATA)
sys.path.append(RESEARCH+"/06_Methods/05_Code/03_DataReduction/libraries/")


def debug(*args, end='\n',fmt='{} ',sep='->', file=None):
    try:
        st = inspect.stack()[1]
        funcName = st[3]
        funcCallStr = st[4]

        varnames = re.search('debug\((.*)\)', funcCallStr[0])
        varnames = varnames.groups()[0].split(',')

        for n, v in zip(varnames, args):
            v_str = str(v)
            v_str = "`%s`"%v_str if v_str.count('\n') == 0 else v_str
            print(fmt.format(n.strip())+sep, v_str, end=end, file=file)
        
    except Exception as err:
        print('debug(...error...)')

if __name__ == '__main__':



    def test_debug():
        """ test debug """
        foobar = [1,2,3]
        foolist = ["a","b"]

        debug(foobar, foolist)
        debug(foobar, foolist, end='\n', fmt='{}', sep=':=')


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

    import tempfile

    # @contextlib.contextmanager
    # def make_temp_directory():
    #     temp_dir = tempfile.mkdtemp()
    #     yield temp_dir
    #     shutil.rmtree(temp_dir)
    #

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
        

    test_datatree()
    
    # def test_datatree_sub():
    #
    #     # empty sub
    #     d1 = DataTree()
    #     d1.a.b = 'foobar'
    #
    #     print('d1:',d1)
    #
    # test_datatree_sub()
    
    ## Run Tests
    test_debug()

    test_bindMethod()
    
    test_grouper()


        # def testDataArray():
        #     print("""docstring for testDataArray""")
        #
        #     xyz = DataArray(array=[1,2,3], label="Testing XYZ", units="mm")
        #
        #     data = DataTree()
        #     data.xyz = xyz
        #
        #     debug(xyz)
        #
        #     debug( data.xyz )
        #
        #     foo = data.xyz
        #     debug( foo )
        #
        # testDataArray()

    import codecs

    from os import environ, path, fdopen, popen
    from traceback import extract_tb
    from cgi import escape
    from urllib.parse import quote

    # # add utf-8 support to stdout/stderr
    # sys.stdout = codecs.getwriter('utf-8')(sys.stdout);
    # sys.stderr = codecs.getwriter('utf-8')(sys.stderr);
    #
    # def project_exceptions(e_type, e, tb):
    #     """
    #     sys.excepthook(type, value, traceback)
    #     This function prints out a given traceback and exception to sys.stderr.
    #
    #     When an exception is raised and uncaught, the interpreter calls sys.excepthook with three arguments,
    #     the exception class, exception instance, and a traceback object. In an interactive session this happens
    #     just before control is returned to the prompt; in a Python program this happens just before the program
    #     exits. The handling of such top-level exceptions can be customized by assigning another three-argument
    #     function to sys.excepthook.
    #     """
    #
    #     # get the file descriptor.
    #     error_fd = int(str(environ['TM_ERROR_FD']))
    #     io = fdopen(error_fd, 'wb', 0)
    #
    #     def ioWrite(s):
    #         # if isinstance(message, unicode):
    #         io.write(bytes(s, 'UTF-8'))
    #
    #     ioWrite("<div id='exception_report' class='framed'>\n")
    #
    #     if isinstance(e_type, str):
    #         ioWrite("<p id='exception'><strong>String Exception:</strong> %s</p>\n" % escape(e_type))
    #     elif e_type is SyntaxError:
    #         # if this is a SyntaxError, then tb == None
    #         filename, line_number, offset, text = e.filename, e.lineno, e.offset, e.text
    #         url, display_name = '', 'untitled'
    #         if not offset: offset = 0
    #         ioWrite("<pre>%s\n%s</pre>\n" % (escape(e.text).rstrip(), "&nbsp;" * (offset-1) + "↑"))
    #         ioWrite("<blockquote><table border='0' cellspacing='0' cellpadding='0'>\n")
    #         if filename and path.exists(filename):
    #             url = "&url=file://%s" % quote(filename)
    #             display_name = path.basename(filename)
    #         if filename == '<string>': # exception in exec'd string.
    #             display_name = 'exec'
    #         ioWrite("<tr><td><a class='near' href='txmt://open?line=%i&column=%i%s'>" %
    #                                                     (line_number, offset, url))
    #         ioWrite("line %i, column %i" % (line_number, offset))
    #         ioWrite("</a></td>\n<td>&nbsp;in <strong>%s</strong></td></tr>\n" %
    #                                             (escape(display_name)))
    #         ioWrite("</table></blockquote></div>")
    #     else:
    #         message = ""
    #         if e.args:
    #             # For some reason the loop below works, but using either of the lines below
    #             # doesn't
    #             # message = ", ".join([str(arg) for arg in e.args])
    #             # message = ", ".join([unicode(arg) for arg in e.args])
    #             message = repr(e.args[0])
    #             if len(e.args) > 1:
    #                 for arg in e.args[1:]:
    #                     message += ", %s" % repr(arg)
    #             ioWrite("<p id='exception'><strong>%s:</strong> %s</p>\n" %
    #                                     (e_type.__name__, escape(message)))
    #
    #     if tb: # now we write out the stack trace if we have a traceback
    #         ioWrite("<blockquote><table border='0' cellspacing='0' cellpadding='0'>\n")
    #         for trace in extract_tb(tb):
    #             filename, line_number, function_name, text = trace
    #             url, display_name = '', 'untitled'
    #             if filename and path.exists(filename):
    #                 url = "&url=file://%s" % quote(path.abspath(filename))
    #                 display_name = path.basename(filename)
    #             ioWrite("<tr><td><a class='near' href='txmt://open?line=%i%s'>" %
    #                                                             (line_number, url))
    #             if filename == '<string>': # exception in exec'd string.
    #                 display_name = 'exec'
    #             if function_name and function_name != "?":
    #                 if function_name == '<module>':
    #                     ioWrite("<em>module body</em>")
    #                 else:
    #                     ioWrite("function %s" % escape(function_name))
    #             else:
    #                 ioWrite('<em>at file root</em>')
    #             ioWrite("</a> in <strong>%s</strong> at line %i</td></tr>\n" %
    #                                                 (escape(display_name).encode("utf-8"), line_number))
    #             ioWrite("<tr><td><pre class=\"snippet\">%s</pre></tr></td>" % text)
    #         ioWrite("</table></blockquote></div>")
    #     if e_type is UnicodeDecodeError:
    #         ioWrite("<p id='warning'><strong>Warning:</strong> It seems that you are trying to print a plain string containing unicode characters.\
    #             In many contexts, setting the script encoding to UTF-8 and using plain strings with non-ASCII will work,\
    #             but it is fragile. See also <a href='http://macromates.com/ticket/show?ticket_id=502C2FDD'>this ticket.</a><p />\
    #             <p id='warning'>You can fix this by changing the string to a unicode string using the 'u' prefix (e.g. u\"foobar\").</p>")
    #     io.flush()
    #
    # print("project_exceptions",project_exceptions)
    # sys.excepthook = project_exceptions

    # def _trace(frame, event, arg):
    #     if event == 'exception':
    #         sys.stderr.write("Exception::arg:"+str(arg)+"\n")
    #         # while frame is not None:
    #         #     filename, lineno = frame.f_code.co_filename, frame.f_lineno
    #         #     sys.stderr.write("_trace exc frame: " + filename \
    #         #         + " " + str(lineno) + " " + str(frame.f_trace) + str(arg) + "\n")
    #         #     if arg[0] == IOError:
    #         #         myexcepthook(arg[0], arg[1], arg[2])
    #         #     frame = frame.f_back
    #
    #     return _trace
    #
    # # sys.settrace(_trace)


    # import cgitb
    # cgitb.enable(format='html')
