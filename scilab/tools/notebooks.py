#!/usr/bin/env python3

import os, sys, functools, itertools, collections, re, logging, json, time, yaml

from collections import OrderedDict

from IPython.display import display
from IPython.display import *

def yamlDisp(msg):
    yamlmsg = yaml.dump(json.loads(json.dumps(msg)))
    display(Markdown("\n\n```yaml\n{}\n```\n\n".format(yamlmsg)))

def jsonDisp(msg):
    jsonmsg = json.loads(json.dumps(msg))
    display(Markdown("\n\n```json\n{}\n```\n\n".format(jsonmsg)))

def codeDisp(msg, code="yaml"):
    display(Markdown("\n\n```{code}\n{msg}\n```\n\n".format(**locals())))

def markDisp(msg):
    display(Markdown(msg))

