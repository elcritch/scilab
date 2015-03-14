#!/usr/bin/env python3

import os, sys, pathlib, re, itertools
import pandas as pd
import numpy as np
import scipy.io as sio
from pandas import ExcelWriter

import matplotlib
matplotlib.use('Qt4Agg')

import scilab.tools.jsonutils as Json
from scilab.tools.project import *
from scilab.expers.configuration import *
from scilab.tools.instroncsv import *

from scilab.datahandling.datahandlers import *
import scilab.datahandling.columnhandlers as columnhandlers  

import numpy as np
import matplotlib.pyplot as plt


def display(*args, **kwargs):
    print(*args, **kwargs)

def HTML(arg):
    return arg
    
def tag(*args, env={}, **kwargs):
    pair = getpropertypair(kwargs)
    return "<{name}>{fmt}</{name}>".format(name=pair[0],fmt=pair[1].format(*args, **env))


def handle_grapher(graph, test, matdata, args, zconfig):
    
    ## Save Summaries ##
    # testfolder.save_calculated_json(name='summaries', data={'step04_cycles':data.summaries})
    
    ## Figure ##
    fig, ax = graph(test=test, matdata=matdata, args=args, step_idx='idx_neg_1', zconfig=zconfig)
    
    # plt.show(block=True)
    
    figname = getfileheaders("graph", test, headers=list(zconfig.items())+[('graph',graph.__name__)])
    # figname = "graph (test={short} | stage={stage} | item={item} | method={method} | v{version})"
    # figname = figname.format(short=test.info.short, version=args.version, **zconfig)
    print(tag(b=figname))
    # test.folder.save_graph(name=figname, fig=fig)
    
    plt.close()
    
    # testfolder.save_graph(name='graph_all_'+testname, fig=fig)
    plt.close()


import scilab.graphs.graph_all as graph_all

def run_config(test, args, config, configfile):
    
    # filepath = datafiles[config]
    debug(configfile)
    matdata = load_columns_matlab(configfile)
    
    confignames = ("stage", "method", "item")
    zconfig = OrderedDict(zip(confignames, config))
    
    handle_grapher(graph_all.graph, test, matdata, args, zconfig)


def run(test, args):
    # debug(test, args)
    # print(debugger_summary("run", locals()))
    datafiles = datacombinations(test, args, items=["tracking"], )
    
    config = ("raw", "uts", "tracking")
    
    for config, configfile in flatten(datafiles,astuple=True).items():
        print("Config:",config)
        run_config(test, args, config, configfile)


def test_folder():
    
    import scilab.expers.configuration as config
    import scilab.expers.mechanical.fatigue.uts as exper_uts
    
    parentdir = Path(os.path.expanduser("~/proj/expers/")) / "fatigue-failure|uts|expr1"
    
    pdp = parentdir / 'projdesc.json' 
    print(pdp)
    print(pdp.resolve())
    
    fs = config.FileStructure(projdescpath=pdp,testinfo=exper_uts.TestInfo, verify=True)
    # Test test images for now
    test_dir = fs.tests.resolve()
    testitemsd = fs.testitemsd()
    
    import shutil
    from tabulate import tabulate

    testitems = { k.name: DataTree(info=k, folder=v, data=DataTree() ) for k,v in testitemsd.items()}

    args = DataTree()
    
    
    for name, test in sorted( testitems.items() )[:1]:
        # if name not in ['dec09(gf10.1-llm)-wa-tr-l8-x1']:
        #     continue
        
        print("\n")
        display(HTML("<h2>{} | {}</h2>".format(test.info.short, name)))
    
        folder = fs.testfolder(testinfo=test.info)
    
    #     debug(mapd(flatten(folder), valuef=lambda x: type(x), keyf=lambda x: x))
        
        data = [ (k,v.relative_to(parentdir), "&#10003;" if v.exists() else "<em>&#10008;</em>" ) 
                    for k,v in flatten(folder).items() ]
        data = sorted(data)
    
        display(HTML(tabulate( data, [ "Name", "Folder", "Exists" ], tablefmt ='html' )))
        debug(folder.data.relative_to(parentdir))
        
        args.version = "0"
        args.testname = name
        args.test = test
        args.fs = fs
        
        test.folder = folder
        test.details = Json.load_json_from(folder.details)
        
        run(test, args)
    
def main():
    
    test_folder()
    
if __name__ == '__main__':
    main()
