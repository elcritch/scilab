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
    #debug(list(test.keys()))
    #debug(testraws)
    #debug(kwargs)
    
    testrawsnames = [ k for k in sorted(testraws.keys()) ]
    projectrawsnames = [ k for k in sorted(projectraws.keys()) ]
    
    rawsdatainput = [ 
        ('Project Raws', [0]+projectrawsnames  ),
        ('Test Raw', [0]+testrawsnames ) 
    ]
    
    def showFileDialog(inputchoices, parent, **kwargs):
        
        testrawdir = inputchoices["testraws"]["value"]
        projrawdir = QFileDialog.getExistingDirectory(
                        parent._parent, 
                        'Choose Raws Folder [%s]'%(inputchoices["projectraws"]["key"]),
                        str(inputchoices["projectraws"]["value"]))
        
        
        #debug(testrawdir, projrawdir)

        tgt_testrawtgt, src_projrawdir = Path(testrawdir), Path(projrawdir).resolve()
        #debug(str(tgt_testrawtgt), str(src_projrawdir))
        
        if not tgt_testrawtgt or not src_projrawdir:
            return 
        
        results = forms.fedit([ ('Input', [0, 'No', 'Yes']) ], 
                              title="Copy Raw Files",
                              comment="Copying:\nFrom: `{src}`\nTo: `{tgt}`".format(src=str(src_projrawdir), tgt=str(tgt_testrawtgt)),
                              # apply=apply_dialog,
                              )
        
        #debug(results)
        
        if not results:
            return
        
        
        try:
            if tgt_testrawtgt.exists():
                print("Deleting")
                shutil.rmtree(str(tgt_testrawtgt))
            
            print("Copying", dict(src=str(src_projrawdir), dst=str(tgt_testrawtgt)))
            shutil.copytree(src=str(src_projrawdir), dst=str(tgt_testrawtgt), ignore_dangling_symlinks=True)
            
        except Exception as err:
            ex = traceback.format_exc()
            print(ex)
            parent.showErrorMessage("Error copying files: `%s` -> `%s`"%(str(tgt_testrawtgt), str(src_projrawdir)), ex=ex)
        
        
        
    
    def apply_dialog(data):
        print("[[apply_dialog]]")
        #debug(data)
        
        projectrawsidx, testrawsidx = data
        
        inputchoices = DataTree( )
        inputchoices['testraws'] = DataTree(key=testrawsnames[testrawsidx], value=testraws[testrawsnames[testrawsidx]])
        inputchoices['projectraws'] = DataTree(key=projectrawsnames[projectrawsidx], value=projectraws[projectrawsnames[projectrawsidx]])
        
        #debug(inputchoices)
        
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
    
    
