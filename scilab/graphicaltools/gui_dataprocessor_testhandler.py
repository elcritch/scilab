#!/usr/bin/env python3

# Import PySide classes
import sys, collections, logging, traceback
from PySide.QtCore import *
from PySide.QtGui import *

from scilab.tools.project import *
from pathlib import *
# from fn import _ as __
import formlayout, boltons.tbutils

import scilab
from scilab.expers.configuration import FileStructure
# from scilab.expers.mechanical.fatigue.cycles import TestInfo as TestInfo
# from scilab.expers.mechanical.fatigue.helpers import *
import scilab.tools.jsonutils as Json

import numpy as np

import scilab.expers.configuration as config
from scilab.expers.mechanical.fatigue.cycles import TestInfo



class ProjectContainer():
    
    projectdirchanged = Signal(str)
    projectrefresh = Signal()
    
    def __init__(self):
        self.fs         = None
        self.test_dir   = None
        self.testitemsd = None
        self.args       = None        

    @Slot(str)
    def setprojdir(self, testdir):

        def showErrorMessage(errmsg, dir, ex=None):
            errorfmt = "Invalid project:<br>Dir `{1}`<br>Error `{0}`"
            if ex: 
                errorfmt += "<br>Exception:<br><pre><code>{ex}</code></pre>"
            errorMessageDialog = QErrorMessage(self)
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
                Json.load_json_from(str(projdescpath))
            except Exception as err:
                logging.exception(err)
                showErrorMessage("Error loading project description: ", testdir, ex=traceback.format_exc())
                return
        
        try:
            self.projectdir = projectdir
            self.fs = config.FileStructure(
                        projdescpath=projdescpath,
                        testinfo=TestInfo, 
                        verify=True, 
                        project=projectdir)
        
            self.test_dir = self.fs.tests.resolve()
            self.testitemsd = self.fs.testitemsd()
            self.args = DataTree()

            # = Emit projectdirchanged =
            print("Setting test directory:", self.test_dir)
            self.projectdirchanged.emit(str(projectdir))
            self.projectrefresh.emit()
            
        except Exception as err:
            logging.exception(err)
            # ei = boltons.tbutils.ExceptionInfo.from_current()
            showErrorMessage("Error setting project: ", testdir, ex=traceback.format_exc())
            return

class TestPanelLayout(QFrame, ProjectContainer):
    
    def __init__(self, parent):
        super(TestPanelLayout, self).__init__(parent=parent)
        super(ProjectContainer, self).__init__()
        
        self.testHandler = TestHandler(self)
        
        layout = QVBoxLayout()
                
        self.initUI(layout)
        self.setLayout(layout)
        
        parent.testitemchanged.connect(self.updateDetailPanel)

    def initUI(self, layout):
                
        testInfoPane = QTextEdit(self)
        testInfoPane.setReadOnly(True)
        testInfoPane.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoAll)
        self.testInfoPane = testInfoPane
        ### ButtonLayout

        buttonLayout = QHBoxLayout()
        okButton = QPushButton("Run Image Dims")
        okButton.clicked.connect(self.testHandler.run_image_dims)

        buttonLayout.addWidget(okButton)

        layout.addWidget(testInfoPane)
        layout.addLayout(buttonLayout)
        
        return
        
    @Slot(object)
    def updateDetailPanel(self, curr=None, prev=None):

        infotext = self.testHandler.get_testitem_info(curr)
        self.testInfoPane.setText(infotext)
    


class TestHandler(object):
    
    def __init__(self, parent):        
        self.parent = parent

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

            errstr = repr(err)

            raise err

            return """
            Exception:

            {err}
            """.format(err=errstr)

    def setupTestList(self):

        win = QWidget()
        win.setWindowTitle('Test List')
        win.setMinimumSize(600, 400)
        layout = QVBoxLayout()
        win.setLayout(layout)

        return win

    def run_enterdata(self):

        datalist = [
            ('Area:', str(self._test_measurements.area)),
            ('Min Area:', str(self._test_measurements.min_area)),
            ('Gauge:', str(self._test_measurements.gauge)),
            ]

        dataout = formlayout.fedit(datalist, parent=self)

        self._test_measurements.area = float(dataout[0])
        self._test_measurements.min_area = float(dataout[1])
        self._test_measurements.gauge = float(dataout[2])

        print(self._test_measurements)

        results = '\n## Image Measures\n\n' + str(self._test_measurements)

        self.updateInfoPane(results)

    def run_image_dims(self):
        if not self.current_item or not self.current_testinfo:
            return

        import scilab.expers.mechanical.fatigue.run_image_measure as run_image_measure

        testinfo = self.current_testinfo
        testfolder = self.testfs.testfolder(testinfo=testinfo, ensure_folders_exists=False)
        
        

        measurements = run_image_measure.process_test(testinfo, testfolder)
        results = '\n## Image Measures\n\n' +'\n'.join( "%s = %s"%i for i in sorted(flatten(measurements).items()) )

        self.updateInfoPane(results)


    def updateInfoPane(self, results):
        self._infotext += results

        self.testInfoPane.setText(self._infotext)

        return

    def run_preconditions(self):
        if not self.current_item or not self.current_testinfo:
            return

        import scilab.graphs.precondition_fitting as precondition_fitting 

        testinfo = self.current_testinfo
        testfolder = self.testfs.testfolder(testinfo=testinfo, ensure_folders_exists=False)

        # if not self._test_measurements.area and not self._test_measurements.gauge:
        self.run_enterdata()

        area_diff = abs(self._test_measurements.min_area-self._test_measurements.area)
        area_min = self._test_measurements.min_area
        N = 5 if area_diff > 1E-3 else 1
        
        results = "# Preconds: \n"
        results += str(self._test_measurements) + "\n"
        
        for a in np.linspace(self._test_measurements.min_area, self._test_measurements.area, N):
            
            print("#### run_preconditions Area:", a)
            # self.updateInfoPane("\nArea:"+str(a)+"\n")

            measures = DataTree(area=a, gauge=self._test_measurements.gauge)

            measurements = precondition_fitting.process_test(testinfo, testfolder, measures)

            data = Json.load_json(testfolder.jsoncalc, json_url=testinfo.name+'.preconds.calculated.json')

            #results += '\n\n## Preconds area: %5.4f\n\n'%(a) 
            # results += '\n'.join( "%s = %s"%i for i in sorted(flatten(data).items()) if '3third' in i[0] )

            results += '\n %6.4f, %6.4f \n'%( measures.area, data['dynmodfits']['3third']['value'])
            
        self.updateInfoPane(results)

