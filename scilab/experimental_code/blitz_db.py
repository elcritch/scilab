#!/usr/bin/env python3

import sys, os

from blitzdb import Document

class Actor(Document):
    pass

class Movie(Document):
    pass

the_godfather = Movie({'name': 'The Godfather','year':1972,'pk':1})

marlon_brando = Actor({'name':'Marlon Brando','pk':2})
al_pacino = Actor({'name' : 'Al Pacino','pk':3})



print("Backend")
from blitzdb import FileBackend

loc = "./my-db"
backend = FileBackend(loc)

print("Created Backend", loc)

the_godfather.save(backend)
marlon_brando.save(backend)
al_pacino.save(backend)

print("Backend Saved and committed:", os.path.realpath(os.curdir))


# print(backend.get(Movie,{'pk':1}))
# or...
the_godfather = backend.get(Movie,{'name' : 'The Godfather'})
print("the_godfather",the_godfather)

the_godfather.cast = {'Don Vito Corleone' : marlon_brando, 'Michael Corleone' : al_pacino}

#Documents stored within other objects will be automatically converted to database references.

marlon_brando.performances = [the_godfather]
al_pacino.performances = [the_godfather]

marlon_brando.save(backend)
al_pacino.save(backend)
the_godfather.save(backend)



backend.create_index(Actor,'performances')
#Will create an index on the 'performances' field, for fast querying

godfather_cast = backend.filter(Actor,{'movies' : the_godfather})
print("godfather_cast",godfather_cast)
#Will return 'Al Pacino' and 'Marlon Brando'


print(backend.get(Movie,{'name' : 'The Godfather'}))
