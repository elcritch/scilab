#!/usr/bin/env python3

import os, sys, pathlib, re, itertools
import pandas as pd
import numpy as np
import scipy.io as sio
from pandas import ExcelWriter

import matplotlib
matplotlib.use('Agg')
# matplotlib.use('Qt4Agg')

import scilab.tools.jsonutils as Json
from scilab.tools.project import *
from scilab.expers.configuration import *
from scilab.tools.instroncsv import *

from scilab.datahandling.datahandlers import *
import scilab.datahandling.columnhandlers as columnhandlers  
import scilab.utilities.merge_calculated_jsons as merge_calculated_jsons

import numpy as np
import matplotlib.pyplot as plt
import scilab.datahandling.processingreports as processingreports

import seaborn as sns

def display(*args, **kwargs):
    print(*args, **kwargs)

def HTML(arg):
    return arg
    
def tag(*args, env={}, **kwargs):
    pair = getpropertypair(kwargs)
    return "<{name}>{fmt}</{name}>".format(name=pair[0],fmt=pair[1].format(*args, **env))

gconfigs = DataTree()
gconfigs['norm', 'precond', 'tracking', 'graph_precond_fit', 'step_idx'] = 'idx_1'


def handle_grapher(graphmod, test, matdata, args, zconfig):
    
    graphname = graphmod.__name__.split('.')[-1]
    
    print(tag(h3="Running Config: {}".format(graphmod.__name__)))
    ## Save Summaries ##
    # testfolder.save_calculated_json(name='summaries', data={'step04_cycles':data.summaries})
    
    ## Figure ##
    graphdata = graphmod.graph(test=test, matdata=matdata, args=args, 
                step_idx=gconfigs[tuple(zconfig.values())+(graphname, 'step_idx',)],
                zconfig=zconfig)
    
    if not graphdata:
        return
    
    # plt.show(block=True)
    # test.folder.save_calculated_json(test=test, name='graphs', data=graphdata.calcs)
    
    figname = getfileheaders("graph", test, suffix="png", 
                                    headers=list(zconfig.items())+[('graph',graphname[len('graph_'):])], 
                                    version=args.options["graphicsrunner"]["version"])
    print(tag(b="Figure: "+figname))
    
    test.folder.save_graph(filename=figname, fig=graphdata.fig)
    
    plt.close()

# =================
# = Graphs Import =
# =================
import scilab.datagraphs.graph_imagemeasurement as graph_imagemeasurement
import scilab.datagraphs.graph_overview as graph_overview
import scilab.datagraphs.graph_precond_fit as graph_precond_fit
import scilab.datagraphs.graph_uts as graph_uts

def run_config(test, args, config, configfile):
    
    print(tag(h2="Running Config: {}".format(config)))
    
    confignames = ("stage", "method", "item")
    zconfig = OrderedDict(zip(confignames, config))
    
    if zconfig["method"] in args.options["dataprocessor","testconfs"].get("skip_methods",""):
        print("**Skipping Method**: `{}` ".format(zconfig))
        return
    
    # filepath = datafiles[config]
    debug(configfile)
    matdata = load_columns_matlab(configfile)
    
    # sns.set_style("whitegrid")
    sns.set_style("ticks")
    sns.set_style("whitegrid")
    
    handle_grapher(graph_imagemeasurement, test, matdata, args, zconfig)
    handle_grapher(graph_overview, test, matdata, args, zconfig)
    handle_grapher(graph_precond_fit, test, matdata, args, zconfig)
    handle_grapher(graph_uts, test, matdata, args, zconfig)

    print(mdHeader(2, "Merging JSON Data"))
    merge_calculated_jsons.handler(testinfo=test.info, testfolder=test.folder, args=args, savePrevious=True)



def run(test, args):
    # debug(test, args)
    # print(debugger_summary("run", locals()))
    datafiles = datacombinations(test, args, items=["tracking"], )
    
    config = ("raw", "uts", "tracking")
    
    for config, configfile in flatten(datafiles,astuple=True).items():
        print("Config:",config)
        run_config(test, args, config, configfile)

    # print(mdHeader(2, "Generating Report and summary data"))
    # processingreports.process_test(testconf=test, args=args)


def test_folder():
    
    import scilab.expers.configuration as config
    
    # parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "fatigue-failure|uts|expr1"
    # parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper|fatigue-failure|uts|trial1"
    # parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper|fatigue-failure|uts|trial3"
    
    pdp = parentdir / 'projdesc.json' 
    print(pdp)
    print(pdp.resolve())
    
    fs = config.FileStructure(projdescpath=pdp, verify=True)
    # Test test images for now
    test_dir = fs.tests.resolve()
    testitemsd = fs.testitemsd()
    
    import shutil
    from tabulate import tabulate

    testitems = { k.name: DataTree(info=k, folder=v, data=DataTree() ) for k,v in testitemsd.items()}

    args = DataTree()
    args.version = "12"
    args.options = DataTree()
    args.options["output", "generatepdfs"] = True
    
    # args.testname = name
    # args.test = test
    # args.fs = fs
    
    for name, test in sorted( testitems.items() )[:]:
        # if name not in ["nov24(gf9.2-lmm)-wf-lg-l4-x2"]:
            # continue
        
        print("\n")
        display(HTML("<h2>{} | {}</h2>".format(test.info.short, name)))
    
        folder = fs.testfolder(testinfo=test.info)
        
        # debug(mapd(flatten(folder), valuef=lambda x: type(x), keyf=lambda x: x))
        
        data = [ (k,v.relative_to(parentdir), "&#10003;" if v.exists() else "<em>&#10008;</em>" ) 
                    for k,v in flatten(folder).items() ]
        data = sorted(data)
        
        display(HTML(tabulate( data, [ "Name", "Folder", "Exists" ], tablefmt ='html' )))
        debug(folder.data.relative_to(parentdir))
        
        test.folder = folder
        test.projectfolder = fs
        test.details = Json.load_json_from(folder.details)
        
        run(test, args)
    
def main():
    
    test_folder()
    
# if __name__ == '__main__':
#     main()
