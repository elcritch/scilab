#!/usr/bin/env python3

# Import PySide classes
import sys, collections
from PySide.QtCore import *
from PySide.QtGui import *

from scilab.tools.project import *
from pathlib import *
# from fn import _ as __
import formlayout

import scilab
from scilab.expers.configuration import FileStructure
# from scilab.expers.mechanical.fatigue.cycles import TestInfo as TestInfo
# from scilab.expers.mechanical.fatigue.helpers import *
import scilab.tools.jsonutils as Json

import numpy as np

import scilab.expers.configuration as config
from scilab.expers.mechanical.fatigue.cycles import TestInfo

class TestPanelLayout(QFrame):
    
    def __init__(self, parent):
        super(TestPanelLayout, self).__init__(parent=parent)
        
        self.testHandler = TestHandler()
        
        layout = QVBoxLayout()
                
        self.initUI(layout)
        self.setLayout(layout)

    def initUI(self, layout):
                
        testInfoPane = QTextEdit(self)
        testInfoPane.setReadOnly(True)
        testInfoPane.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoAll)
        
        ### ButtonLayout

        buttonLayout = QHBoxLayout()
        okButton = QPushButton("Run Image Dims")
        dataButton = QPushButton("Enter Data")
        cancelButton = QPushButton("Run Preconditions Fit")
        okButton.clicked.connect(self.testHandler.run_image_dims)
        cancelButton.clicked.connect(self.testHandler.run_preconditions)
        dataButton.clicked.connect(self.testHandler.run_enterdata)

        buttonLayout.addWidget(dataButton)
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)

        layout.addWidget(testInfoPane)
        layout.addLayout(buttonLayout)
        
        return
        
    def actionUpdateDetailPanel(self, curr=None, prev=None):

        debug(type(curr), repr(curr), repr(prev))
        self._test_measurements = DataTree(area="", min_area="", gauge="")

        item = self.testList.getitem(curr.text() if curr else None)
        self.current_item = item
        self.current_testinfo = TestInfo(name=item.name) if item else None

        self._infotext = self.get_testitem_info(self.current_item, self.current_testinfo)
        self.testInfoPane.setText(self._infotext)
    


class TestHandler(object):
    
    def __init__(self):
        
        # self.testfs = test_filestructure
        # self.projectdir = test_filestructure.projectspath.resolve()
        # self.projectdir = file_dir
        self.current_item = None
        self.current_testinfo = None
        
    def setupTestDir(self):
        
    
        fs = config.FileStructure(projdescpath=pdp,testinfo=exper.TestInfo, verify=True, project=args.parentdir)
        # Test test images for now
        test_dir = fs.tests.resolve()
        testitemsd = fs.testitemsd()

        debug(test_dir)
    
        args = DataTree()
    
        # parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "fatigue-failure|uts|expr1"
        # args.parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper|fatigue-failure|cycles|trial1"
    
        # pdp = args.parentdir / 'projdesc.json' 
        # print(pdp)
        # print(pdp.resolve())
        
        

    def get_testitem_info(self, item, testinfo):

        if not item or not testinfo:
            return


        def getsubfolders(items, pd):
            return '\n'.join(map(lambda x: str(x.relative_to(pd)), images))

        try:

            projectdir = self.projectdir

            images = []
            images += list(item.rglob("*.JPG"))
            images += list(item.rglob("*.JPG"))

            otherfiles = []
            otherfiles += list(item.rglob('*'))
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

