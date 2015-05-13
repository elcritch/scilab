#!/usr/local/bin/python3

import sys, multiprocessing
import queue
from collections import defaultdict
from os import getpid
from io import StringIO
from multiprocessing import *
# import Queue as PyQueue


# http://www.codeitive.com/0SHgjVkejq/python-multiprocessing-synchronizing-filelike-object.html 

class MultiProcessFile(object):
    """
    helper for testing multiprocessing

    multiprocessing poses a problem for doctests, since the strategy
    of replacing sys.stdout/stderr with file-like objects then
    inspecting the results won't work: the child processes will
    write to the objects, but the data will not be reflected
    in the parent doctest-ing process.

    The solution is to create file-like objects which will interact with
    multiprocessing in a more desirable way.

    All processes can write to this object, but only the creator can read.
    This allows the testing system to see a unified picture of I/O.
    """
    def __init__(self):
        # per advice at:
        #    http://docs.python.org/library/multiprocessing.html#all-platforms
        self.__master = getpid()
        self.__queue = multiprocessing.Manager().Queue()
        self.__buffer = StringIO()
        self.softspace = 0

    def buffer(self):
        if getpid() != self.__master:
            return

        cache = defaultdict(str)
        while True:
            try:
                pid, data = self.__queue.get_nowait()
            except queue.Empty:
                break
            
            cache[pid] += data
        
        for pid in sorted(cache):
            self.__buffer.write( '[[thread:%s]] %r\n' % (pid, cache[pid]) )
            
    def write(self, data):
        self.__queue.put((multiprocessing.current_process()._identity, data))
        
    def __iter__(self):
        "getattr doesn't work for iter()"
        self.buffer()
        return self.__buffer

    def getvalue(self):
        self.buffer()
        return self.__buffer.getvalue()

    def flush(self):
        pass



if __name__ == '__main__':
    
    def printer(args):
        msg, stdout = args
         
        sys.stdout = stdout
        
        print("My msg %d "%multiprocessing.current_process()._identity, "::", msg, "\n")
        


    print('Starting')
    import sys
    stdoutqueue = MultiProcessFile()
    # sys.stdout = buffer

    pool = Pool(5)
    
    pool.map_async(printer, [ (i, stdoutqueue) for i in range(20) ])
    
    pool.join()
    
    # sys.stdout = sys.__stdout__
    # sys.stderr = sys.__stderr__

    print()
    print('Threading Done')
    print()
    stdoutqueue.buffer()
    print("buffer", "`%s`"%stdoutqueue.getvalue())
    