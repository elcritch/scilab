#!/usr/bin/env python3
# coding: utf-8

import os, sys, functools, itertools, collections, re, logging, json
from pathlib import *


def mapTo(func, iterable,*args,**kwargs):
    return [ (i, func(i,*args,**kwargs)) for i in iterable ]

def debugger(func, debug=False):
    """ Use to annotate functions for debugging purposes. """
    
    def debugger_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as err:
            args = itertools.chain( enumerate(args), kwargs.items())
            args = [ "{}-> {}".format(k, str(v)) for k,v in args ] 
            print("Trace:", func,' Args :=', ', '.join(args), flush=True,file=sys.stderr)
            raise err
    return debugger_wrapper    



def main():
    
    print("test:debugger:\n")
    
    @debugger
    def foo(a,b=None):
        return a+b
        
    @debugger
    def bar(a,fmt, b=None):
        return fmt.format(str(foo(a,b)))
        
    print(foo(1,2))
    
    try:
        print("error")
        print(foo(1))
    except Exception as e:
        print("Error:", e,file=sys.stderr)
    
    print("\n",file=sys.stderr)
    
    try:
        print("\nFail:")
        print(bar(10,b=(3,),fmt="{}"))
    except Exception as e:
        print("Error:", e,file=sys.stderr)

    try:
        print("\nSuccess:")
        print(bar(10,b=3,fmt="{}"))
    except Exception as e:
        print("Error:", e,file=sys.stderr)

if __name__ == '__main__':
    
    main()
