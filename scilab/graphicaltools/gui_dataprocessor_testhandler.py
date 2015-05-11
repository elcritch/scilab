#!/usr/bin/env python3

# Import PySide classes
import sys, collections, logging, traceback

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import QWebView
from PyQt5.QtWebKit import QWebSettings
from PyQt5.QtNetwork import QNetworkRequest

Signal = pyqtSignal
Slot = pyqtSlot

from scilab.tools.project import *
from pathlib import *
# from fn import _ as __
# import formlayout
# import boltons.tbutils

import scilab
from scilab.expers.configuration import FileStructure
# from scilab.expers.mechanical.fatigue.cycles import TestInfo as TestInfo
# from scilab.expers.mechanical.fatigue.helpers import *
import scilab.tools.jsonutils as Json
from scilab.datahandling.datahandlers import *

import numpy as np

import scilab.expers.configuration as config
from scilab.expers.configuration import BasicTestInfo


class ProjectContainer():
    
    projectdirchanged = Signal(str)
    projectrefresh = Signal()
    createnewtest = Signal()
    
    def __init__(self):
        self.fs         = None
        self.test_dir   = None
        self.testitemsd = None
        self.args       = None  
        self.projectdesc = None
    
    @Slot()
    def docreatenewtest(self):
        
        # TODO: show input dialog... 
        userinputstr = "Get user input here..."
        testinfoinput = self.fs.testinfo.parse(userinputstr)
        
        self.fs.makenewfolder(**testinfoinput._asdict())
        
        # TODO: refresh test list
        # TODO: select new test
        
    @Slot(object)
    def setprojdir(self, testdir):
        
        debug(testdir)
        
        def showErrorMessage(errmsg, dir, ex=None):
            errorfmt = "Invalid project:<br>Dir `{1}`<br>Error `{0}`"
            if ex: 
                errorfmt += "<br>Exception:<br><pre><code>{ex}</code></pre>"
            errorMessageDialog = QErrorMessage(self._parent)
            errorMessageDialog.showMessage(errorfmt.format(errmsg, dir, ex=ex))
        
        projectdir = Path(str(testdir))
        
        if not projectdir.exists():
            showErrorMessage("Project folder does not exist.", testdir)
            return
        
        projdescpath = projectdir / "projdesc.json"
        
        if not projdescpath.exists():
            showErrorMessage(" Missing projectdesc file.", str(projectdir))
            return
        else:
            try:
                projdescpath.resolve()
                self.projectdesc = Json.load_json_from(str(projdescpath))
            except Exception as err:
                logging.exception(err)
                showErrorMessage("Error loading project description: ", testdir, ex=traceback.format_exc())
                return
        
        try:
            self.projectdir = projectdir
            self.fs = config.FileStructure(projdescpath=projdescpath,verify=True)
        
            self.test_dir = self.fs.tests.resolve()
            self.testitemsd = self.fs.testitemsd()
            self.args = DataTree()

            # = Emit projectdirchanged =
            print("Setting test directory:", self.test_dir)
            self.projectdirchanged.emit(str(projectdir))
            self.projectrefresh.emit()
            
        except Exception as err:
            traceback.print_exc(file=sys.stderr)
            
            # ei = boltons.tbutils.ExceptionInfo.from_current()
            # raise err
            
            showErrorMessage("Error setting project: ", testdir, ex=traceback.format_exc())
            return


class TestHandler(QObject, ProjectContainer):
    
    def __init__(self, parent):        
        super(TestHandler, self).__init__(parent=parent)
        super(ProjectContainer, self).__init__()
        self._parent = parent

    def setitem(self, item):
        self.test = DataTree()
        self.test.info = item.test
        self.test.folder = self.fs.testfolder(testinfo=self.test.info, ensure_folders_exists=False)
        print("Setting Test:", self.test)

    def getitem(self):
        
        return self.test

    def getinfopanelhtml(self, item):
        
        print("HTML:", self.test.folder.main)
        reportUrl = next(self.test.folder.main.glob("report*.html"), None)
        
        debug(reportUrl)
        if reportUrl and reportUrl.exists():
            with reportUrl.open('rb') as reportFile:            
                reportHtmlStr = reportFile.read().decode(encoding='UTF-8')
        else:
            reportHtmlStr = ""
        
        return reportHtmlStr, self.test.folder.main

    def get_testitem_info(self, item):

        if not item:
            return

        testinfo = item.test
        
        def getsubfolders(items, pd):
            return '\n'.join(map(lambda x: str(x.relative_to(pd)), images))

        try:

            projectdir = self.parent.projectdir

            images = []
            images += list(item.folder.rglob("*.JPG"))
            images += list(item.folder.rglob("*.JPG"))

            otherfiles = []
            otherfiles += list(item.folder.rglob('*'))
            otherfiles = otherfiles[:100] # safety test for now.

            return """
            Project: {testinfo}
            Directory: {testfolder}

            Images:

            {images}

            Other files:

            {otherfiles}
            """.format(testinfo=str(testinfo),
                        testfolder=str(projectdir),
                        images=getsubfolders(images,projectdir),
                        otherfiles=getsubfolders(otherfiles,projectdir),
                        ).strip().replace('\n            ','\n')

        except Exception as err:
            traceback.print_exc(file=sys.stdout)
            
            errstr = repr(err)
            # raise err
            return """
            Exception:

            {err}
            """.format(err=errstr)



    def updateInfoPane(self, results):
        self._infotext += results

        self.testInfoPane.setText(self._infotext)

        return


