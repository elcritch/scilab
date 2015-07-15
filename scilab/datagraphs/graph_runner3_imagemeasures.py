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
import scilab.datahandling.processingreports as processingreports

import numpy as np
import matplotlib.pyplot as plt

import seaborn as sns

def display(*args, **kwargs):
    print(*args, **kwargs)

def HTML(arg, whitespace=None):
    if whitespace:
        return "<div style='white-space: {whitespace};'>\n{ret}\n</div>\n".format(whitespace=whitespace, ret=arg)
    else:
        ret = arg.replace('\n','\r')
        return ret
    
def tag(*args, env={}, **kwargs):
    pair = getpropertypair(kwargs)
    return "<{name}>{fmt}</{name}>".format(name=pair[0],fmt=pair[1].format(*args, **env))

gconfigs = DataTree()
gconfigs['norm', 'm2_precond', 'tracking', 'graph_precond_fit', 'step_idx'] = 'idx_1'


def handle_grapher(graphmod, test, matdata, args, zconfig, kw_grapher):
    
    graphname = graphmod.__name__.split('.')[-1]
    
    print(tag(h3="Running Config: {}".format(graphmod.__name__)))
    ## Save Summaries ##
    # testfolder.save_calculated_json(name='summaries', data={'step04_cycles':data.summaries})
    
    ## Figure ##
    graphdata = graphmod.graph(test=test, matdata=matdata, args=args, 
                step_idx=gconfigs[tuple(zconfig.values())+(graphname, 'step_idx',)],
                zconfig=zconfig, **kw_grapher)
    
    if not graphdata:
        return
    
    # plt.show(block=True)
    
    # if 'cycles' in graphdata.calcs:
    #     print(dir(graphdata['calcs']['cycles']['actual_perc']))
    # jsondata = remap(graphdata.calcs, valuef=lambda k,v: v._asdict() if hasattr(v,'_asdict') else v)
    # debug(jsondata)
    # test.folder.save_calculated_json(test=test, name='graphs', data=jsondata)
    
    figname = getfileheaders("graph", test, suffix="png", 
                                headers=list(zconfig.items())+[('graph',graphname[len('graph_'):])], 
                                version=args.options["graphicsrunner"]["version"])
    print(tag(b="Figure: "+figname))
    
    test.folder.save_graph(filename=figname, fig=graphdata.fig)
    
    
    plt.close()

# =================
# = Graphs Import =
# =================
import scilab.datahandling.processimagemeasurement as processimagemeasurement
import scilab.datagraphs.graph_imagemeasurement as graph_imagemeasurement
import scilab.datagraphs.graph_overview as graph_overview
import scilab.datagraphs.graph_precond_fit as graph_precond_fit
import scilab.datagraphs.graph_cycles_peaks as graph_cycles_peaks
import scilab.datagraphs.graph_cycles_n_to_strain as graph_cycles_n_to_strain
import scilab.datagraphs.graph_cycles_stop as graph_cycles_stop

def run_config(test, args):
    
    zconfig = DataTree()
    
    sns.set_style("ticks")
    sns.set_style("whitegrid")
    
    # === Graphs ===
    handle_grapher(graph_imagemeasurement, test, None, args, zconfig, kw_grapher=DataTree(forceRun=True))

def test_folder():
    
    import scilab.expers.configuration as config
    import scilab.expers.mechanical.fatigue.cycles as exper
    
    args = DataTree()
    args.version = "0"
    args.options = DataTree()
    args.options["output", "generatepdfs"] = True
    
    # args.testname = name
    # args.test = test
    # args.fs = fs
    
    # parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "fatigue-failure|uts|expr1"
    # args.parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper|fatigue-failure|cycles|trial1"
    args.parentdir = list(Path("/Users/jaremycreechley/proj/phd-research/").resolve().glob("verification*"))[0]
    args.options = DataTree()
    args.options["graphicsrunner","version"] = "2"
    
    debug(args.parentdir.resolve())
    pdp = args.parentdir / 'projdesc.json' 
    print(pdp)
    print(pdp.resolve())
    
    fs = config.FileStructure(projdescpath=pdp, verify=True, project=args.parentdir)
    # Test test images for now
    test_dir = fs.tests.resolve()
    testitemsd = fs.testitemsd()
    
    projdesc = fs.projdesc
    
    import shutil
    from tabulate import tabulate
    
    testitems = { k.name: DataTree(info=k, folder=v, data=DataTree() ) for k,v in testitemsd.items() }
    
    summaries = OrderedDict()
    
    for name, test in sorted( testitems.items() )[:]:
        # if name not in ["jan11(gf11.5-llm)-wa-lg-l6-x1"]:
            # continue
        # if name not in ["jan11(gf11.5-llm)-wa-lg-l6-x1"]:
            # continue
        
        print("\n")
        display(HTML("<h2>{} | {}</h2>".format(test.info.short, name)))
    
        folder = fs.testfolder(testinfo=test.info)
    
    #     debug(mapd(flatten(folder), valuef=lambda x: type(x), keyf=lambda x: x))
        
        data = [ (k,v.relative_to(args.parentdir), "&#10003;" if v.exists() else "<em>&#10008;</em>" ) 
                    for k,v in flatten(folder).items() ]
        data = sorted(data)
    
        display(HTML(tabulate( data, [ "Name", "Folder", "Exists" ], tablefmt ='html' )))
        debug(folder.data.relative_to(args.parentdir))
        
        test.folder = folder
        test.projectfolder = fs
        test.details = Json.load_json_from(folder.details)
        test.projdesc = projdesc
        
        
        state = DataTree()
        state.args = args
        state.args.testconf = test
        state.position = []
        print(mdHeader(2, "Run Image Measurement"))
    
        imageconfstate = state.set(image_measurement=projdesc["experiment_config","config","calibration","image_measurement"])
        
        try:
            
            processimagemeasurement.process_test(test, imageconfstate, args)
            run_config(test, args)
            summaries[name] = "Success", "", ""
        except Exception as err:
            # summaries[name] = "Failed"
            summaries[name] = "Failed", str(err), "<a src='file://{}'>Folder</a>".format(test.folder.testdir.as_posix())
            logging.exception(err)
            raise err
    
    print("Summaries:\n\n")
    print(HTML(tabulate( [ (k,)+v for k,v in summaries.items()], [ "Test Name", "Status", "Error", "Folder" ], tablefmt ='pipe' ), whitespace="pre-wrap"))
    print()
    
def main():
    
    test_folder()
    
if __name__ == '__main__':
    main()
