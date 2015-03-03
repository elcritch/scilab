#!/usr/bin/env python3
# from typing import *

import os, sys, pathlib, collections

from scilab.tools.project import *
from scilab.expers.configuration import *
from scilab.tools.instroncsv import *
import scilab.tools.jsonutils as Json


class Shapes(object):
    def __init__(self, subs=tuple()):
        self.subs = tuple(subs)
    def __repr__(self):
        return type(self).__name__ + ( str([ s for s in self.subs ]) if self.subs else "")
    def __eq__(self, other):
        return repr(self) == repr(other) 
    def __hash__(self):
        return object.__hash__(type(self))

class Any(Shapes): pass
class Array(Shapes): pass
class String(Shapes): pass
class Tuple(Shapes): pass
class JsonDict(Shapes): pass
class Property(JsonDict): pass


def shape(obj):
    
    if isinstance(obj, (list, tuple)):
        subtypes = set()
        for item in obj:
            subtypes.add(shape(item))
        subtype = Any() if len(subtypes) > 1 else next(subtypes.__iter__(),Any)
        return Array(tuple(subtypes))
    elif isinstance(obj, (dict, collections.MutableMapping)):
        if len(obj) == 1:
            return Property( ( shape(next(obj.values().__iter__())), ) )
        elif len(obj) == 0:
            return Property( tuple((None,)) ) 
        else:
            subtypes = set()
            for item in obj.values():
                subtypes.add(shape(item))
            return JsonDict( subtypes )
    else:
        return type(obj).__name__ 

def json_to_excel(json_object):
    
    # debug(json_object)
    
    for sheetname, sheetdata in json_object.items():
        
        print(mdHeader(2,"Sheet: {}".format(sheetname)))
        
        for table in sheetdata:
            debug(shape(table))


    
if __name__ == '__main__':

    with Tests(quiet=False, ) as tests:
    
        foobar = []
    
        @test_in(tests)
        def test_print_headers():

            project_description_url = Path(__file__).parent / "project_description.json"
            debug(project_description_url)
            project_description_url = project_description_url.resolve()    
            project_description = Json.load_json_from(project_description_url)
            
            json_to_excel(project_description)
            
            

