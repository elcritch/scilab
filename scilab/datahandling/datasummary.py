#!/usr/bin/env python3

import os, sys, pathlib, re, logging
import pandas as pd
import numpy as np
import scipy.io as sio
from pandas import ExcelWriter

import scilab.tools.jsonutils as Json
from scilab.tools.project import *
from scilab.expers.configuration import *
from scilab.tools.instroncsv import *

from scilab.datahandling.datahandlers import *
import scilab.datahandling.columnhandlers as columnhandlers  
import scilab.datahandling.datasheetparser as datasheetparser  
import scilab.datahandling.processimagemeasurement as processimagemeasurement
import scilab.utilities.merge_calculated_jsons as merge_calculated_jsons
import scilab.expers.mechanical.fatigue.run_image_measure as run_image_measure

import numpy as np

import shutil
from tabulate import tabulate

# @debugger
def resolve(url):
    return Path(url).resolve()


def process(testconf, state, args):

    pass

# ====================
# = Script Execution =
# ====================

def display(*args, **kwargs):
    print(*args, **kwargs)

def HTML(arg, whitespace=None):
    if whitespace:
        return "<div style='white-space: {whitespace};'>\n{ret}\n</div>\n".format(whitespace=whitespace, ret=arg)
    else:
        ret = arg.replace('\n','\r')
        return ret

def execute(fs, name, testconf, args):
    
    print("\n")
    display(HTML("<h2>Processing Test: {} | {}</h2>".format(testconf.info.short, name)))
    
    folder = fs.testfolder(testinfo=testconf.info)
    
    try:
        processed_link = fs.processed / testconf.info.short 
        if not processed_link.exists():
            debug("../"+str(folder.testdir.relative_to(fs.project)), str(processed_link))
            os.symlink("../"+str(folder.testdir.relative_to(fs.project)), str(processed_link), target_is_directory=True )
    except Exception as err:
        logging.warn("Unable to link processed dir: "+str(err))
    
    data = [ (k,v.relative_to(args.parentdir), "&#10003;" if v.exists() else "<em>&#10008;</em>" ) 
                for k,v in flatten(folder).items() if v ]
    data = sorted(data)

    print()
    print(HTML(tabulate( data, [ "Name", "Folder", "Exists" ], tablefmt ='pipe' ), whitespace="pre-wrap"))
    debug(folder.data.relative_to(args.parentdir))
    
    args.testname = name
    args.testconf = testconf
    args.report = sys.stdout
    
    testconf.folder = folder
    
    # Setup Arguments Environment
    state = DataTree()
    state.args = args
    state.filestructure = fs
    state.position = []
    
    # update json details
    print(mdHeader(2, "Load JSON Data"))
    
    testdetails = Json.load_json_from(testfolder.details)
    state.details = testdetails
    
    print(mdHeader(2, "Update Reports"))

    results = process(testconf=testconf, state=state, args=args)

    return results

def test_folder(args):
    
    import scilab.expers.configuration as config
    
    # parentdir = Path(os.path.expanduser("~/proj/expers/")) / "fatigue-failure|uts|expr1"
    # parentdir = Path(os.path.expanduser("~/proj/expers/")) / "exper|fatigue-failure|cycles|trial1"
    # args.parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper|fatigue-failure|cycles|trial1"
    args.parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper|fatigue-failure|uts|trial1"
    # args.parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper|fatigue-failure|uts|trial3"
    
    pdp = args.parentdir / 'projdesc.json' 
    print(pdp)
    # print(pdp.resolve())
    
    fs = config.FileStructure(projdescpath=pdp, verify=True, project=args.parentdir)
    
        
    # Test test images for now
    test_dir = fs.tests.resolve()
    testitemsd = fs.testitemsd()

    testitems = { k.name: DataTree(info=k, folder=v, data=DataTree() ) for k,v in testitemsd.items()}
    
    summaries = OrderedDict()
    
    
    for name, testconf in sorted( testitems.items() )[:]:
        # if name != "jan13(gf10.2-rlm)-wa-tr-l6-x3":
        # if 'tr' not in name or name < "nov24(gf9.2-llm)-wa-tr-l5-x2":
        # if name < "jan14":
            # continue
        # if name not in ["feb07(gf10.4-llm)-wa-lg-l10-x2"]:
            # continue
        
        try:
            results = execute(fs, name, testconf, args, )
            
            summaries[name] = "Success", "", ""
        except Exception as err:
            logging.error(err)
            summaries[name] = "Failed", str(err), "<a src='file://{}'>Folder</a>".format(testconf.folder.testdir.as_posix())
            raise err
    
    print("Summaries:\n\n")
    print(HTML(tabulate( [ (k,)+v for k,v in summaries.items()], [ "Test Name", "Status", "Error", "Folder" ], tablefmt ='pipe' ), whitespace="pre-wrap"))
    print()

def main():
    # test_run()
    args = DataTree()
    args.forceRuns = DataTree(raw=False, norm=True)
    args.version = "0"
    # args["force", "imagecropping"] = True
    # args["dbg","image_measurement"] = True
    # === Excel === 
    args.options = DataTree()
    args.options["output", "excel"] = False
    # === Only Update Variables === 
    # print("<a src='file:///Users/elcritch/proj/phd-research/exper|fatigue-failure|cycles|trial1/02_Tests/jan10(gf10.9-llm)-wa-lg-l10-x3/'>Test1</a>")
    # print("<a src='file:///Users/elcritch/proj/phd-research/exper%7Cfatigue-failure%7Ccycles%7Ctrial1/02_Tests/jan10%28gf10.9-llm%29-wa-lg-l10-x3/'>Test1</a>")
    test_folder(args)
    
if __name__ == '__main__':
    main()


