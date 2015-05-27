#!/usr/bin/env python3


import sys, collections, logging, traceback, io, multiprocessing, copy, time

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import QWebView
from PyQt5.QtWebKit import QWebSettings
from PyQt5.QtNetwork import QNetworkRequest
from pathlib import *

Signal = pyqtSignal
Slot = pyqtSlot

import scilab.tools.jsonutils as Json
import scilab.graphicaltools.forms as forms
from scilab.tools.project import *
from scilab.tools import testingtools
from scilab.graphicaltools.multifile import *
from scilab.datahandling.datahandlers import *
from scilab.graphicaltools.guitestprocessor import guitestprocess

import scilab.expers.configuration as config


def importrawsdialog(test, **kwargs):
    
    import datetime
    
    print("[Import Raws]")
    testraws = test.folder["raws"]
    projectraws = kwargs["projectfolder"]["raws"]
    
    testfiles = { k:v for k,v in kwargs["projectfolder"]["projdesc"]["experiment_config"]["testfolder"]["filestructure"].items() if "images" in k }
    testimages = kwargs["projectfolder"]["projdesc"]["experiment_config"]["testfolder"]["files"]
    
    #debug(list(test.keys()))
    #debug(testraws)
    #debug(kwargs)
    
    getnames = lambda d: [ k for k in sorted(d.keys()) ]
    testrawsnames = getnames(testraws) + getnames( testimages )
    projectrawsnames = getnames(projectraws) + getnames( testfiles )
    
    testraws.update(testimages)
    projectraws.update(testfiles)
    
    rawsdatainput = [ 
        ('Project Raws', [0]+projectrawsnames  ),
        ('Test Raw', [0]+testrawsnames ),
        ('File?', False)
    ]
    
    def showFileDialog(inputchoices, parent, **kwargs):
        
        testrawdir = inputchoices["testraws"]["value"]
        isfile = inputchoices["File?"]
        
        
        if isfile:
            projrawdir = QFileDialog.getOpenFileName(
                            parent._parent, 
                            'Choose Raws File [%s]'%(inputchoices["projectraws"]["key"]),
                            str())
        else:
            projrawdir = QFileDialog.getExistingDirectory(
                            parent._parent, 
                            'Choose Raws Folder [%s]'%(inputchoices["projectraws"]["key"]),
                            str(inputchoices["projectraws"]["value"]))
        
        
        #debug(testrawdir, projrawdir)

        tgt_testrawtgt, src_projrawdir = Path(testrawdir), Path(projrawdir).resolve()
        #debug(str(tgt_testrawtgt), str(src_projrawdir))
        
        if not tgt_testrawtgt or not src_projrawdir:
            return 
        
        results = forms.fedit([ ('Input', [0, 'Yes', 'No']) ], 
                              title="Copy Raw Files",
                              comment="""
                              <h4>Copying:</h4>
                              <table>
                                  <tr><td><b>From Directory:</b></td><td><small>{srcb}</small></td></tr> \n
                                  <tr><td><b>From Name:</b></td><td>{srcn}</td></tr> \n
                                  <tr><td><b>To Directory:</b></td><td><small>{tgtb}</small></td></tr> \n
                                  <tr><td><b>To Name:</b></td><td>{tgtn}</td></tr> \n
                                  """.format(
                                  srcb=str(src_projrawdir.parent), tgtb=str(tgt_testrawtgt.parent),
                                  srcn=str(src_projrawdir.name), tgtn=str(tgt_testrawtgt.name)
                              ),
                              # apply=apply_dialog,
                              )
        
        #debug(results)
        
        if not results:
            
            forms.fedit([], comment="Caneled import. ")
            
            return
        
        
        try:
            # if tgt_testrawtgt.exists():
            #     print("Deleting")
            #     shutil.rmtree(str(tgt_testrawtgt))
            
            # shutil.copytree(src=str(src_projrawdir), dst=str(tgt_testrawtgt), ignore_dangling_symlinks=True)
            src_projrawdir_files = list(src_projrawdir.glob("*")) if src_projrawdir.is_dir() else [ src_projrawdir ]
            
            for src_file in src_projrawdir_files:
                print("Copying {src} -> {dst} ".format(src=str(src_projrawdir), dst=str(tgt_testrawtgt).encode('utf-8')))
                shutil.copy(src=str(src_file), dst=str(tgt_testrawtgt))
            
            forms.fedit([ ], comment="Done importing! Files copied:<br>\n <table>{files}</table>".format(
                    files= '\n'.join( "<tr><td>{}</td></tr>".format(f) for f in src_projrawdir_files )))
            
        except Exception as err:
            ex = traceback.format_exc()
            print(ex)
            parent.showErrorMessage("Error copying files: `%s` -> `%s`"%(str(tgt_testrawtgt), str(src_projrawdir)), ex=ex)
        
        
        
    
    def apply_dialog(data):
        print("[[apply_dialog]]")
        #debug(data)
        
        projectrawsidx, testrawsidx, isfile = data
        
        inputchoices = DataTree( )
        inputchoices['testraws'] = DataTree(key=testrawsnames[testrawsidx], value=testraws[testrawsnames[testrawsidx]])
        inputchoices['projectraws'] = DataTree(key=projectrawsnames[projectrawsidx], value=projectraws[projectrawsnames[projectrawsidx]])
        inputchoices['File?'] = isfile
        
        debug(inputchoices)
        
        showFileDialog(inputchoices, **kwargs)
        
    
    # rawsdata = forms.fedit(rawsdatainput)
    results = forms.fedit(rawsdatainput, 
                          title="Copy Raw Files",
                          # comment="Choose input raws folder and the output test-raw:",
                          # apply=apply_dialog,
                          )
    
    if not results:
        return 
    
    apply_dialog(results)
    
    
