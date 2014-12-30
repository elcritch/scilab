#!/usr/bin/env python3


import shutil, re, sys, os, itertools, collections
from pathlib import Path


class UtsTestInfo(collections.namedtuple('TestInfo', 'name date set side wedge orientation layer sample run')):

    reTestName = re.compile(r"(\w+\d+)\((..[\d\.]+)-(..m)\)-w([a-f])-(tr|lg)-l(\d+)-x(\d+)(?:-(.+))?")
    
    def __new__(self, name=None, *args, **kwargs):
        if name and not args and not kwargs:
            
            match = self.reTestName.match(name)
            if not match:
                raise Exception("Could not parse test name: "+name)
            
            args = match.groups()
            return super().__new__(self, name, *args)
        else:
            return super().__new__(self, name, *args, **kwargs)
            

    def short(self):
        """ Return a short mnemonic test name. """
        s = self
        strToOrd = lambda s: ''.join(str(ord(c.lower())-ord('a')+1) for c in s)
        batch, batchNumber = map(int,s.set[2:].split('.'))
        return "{0}{1:02d}{5}-{2}{3:02d}{4}".format(
                batch, batchNumber, strToOrd(s.wedge),int(s.layer),s.sample, s.orientation.upper())

    def as_dict(self):
        return { f:v for f,v in zip(self._fields, self[:])}

class ImageSet(collections.namedtuple('TestSet', 'front, side, fail')):
    pass
    
class ImageData(collections.namedtuple('TestData', 'info, parent, full, cropped, cleaned')):
    pass


def main():
    
    print("Test UtsTestInfo")
    
    ti = UtsTestInfo(name='nov26(gf9.2-llm)-wf-tr-l9-x1')
    print(ti)
    
    ti = UtsTestInfo('xx',*UtsTestInfo.reTestName.match('nov26(gf9.2-rmm)-wf-tr-l9-x1-r1').groups())
    ti.short()
    print(ti.short())
    
    print("Success")
    
if __name__ == '__main__':
    main()
    
    
