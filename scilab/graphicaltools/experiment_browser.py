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
from scilab.expers.mechanical.fatigue.cycles import FileStructure
from scilab.expers.mechanical.fatigue.cycles import TestInfo as TestInfo
from scilab.expers.mechanical.fatigue.helpers import *
import scilab.tools.jsonutils as Json

import numpy as np

def supported_image_extensions():
    ''' Get the image file extensions that can be read. '''
    formats = QImageReader().supportedImageFormats()
    # Convert the QByteArrays to strings
    return [str(fmt) for fmt in formats]


class ImageFileList(QListWidget):
    ''' A specialized QListWidget that displays the list
    of all image files in a given directory. '''

    def __init__(self, testfs, parent=None):
        QListWidget.__init__(self, parent)
#        self.testfs = testfs
        self.settestfs(testfs)

    def _populate(self):
        ''' Fill the list with images from the
        current directory in self._dirpath. '''

        # In case we're repopulating, clear the list
        self.clear()

        testitemsd = self.testfs.testitemsd()

        self._testitems = collections.OrderedDict(
                    sorted(
                        ( (name,pth) for name, pth in testitemsd.items() ),
                        key=lambda f: f[1].stat().st_mtime
                    ))

        print("Setting testfolders:", repr(self._testitems))


        for key in self._testitems.keys():
            item = QListWidgetItem(self)
            item.setText(key)

    def getitem(self, text):
        return self._testitems.get(text, None)


    def settestfs(self, testfs):
        ''' Set the current image directory and refresh the list. '''
        self.testfs = testfs
        self._populate()

import importlib

class Example(QWidget):

    def __init__(self, test_filestructure:FileStructure, file_dir):
        super().__init__()

        self.testfs = test_filestructure
        # self.projectdir = test_filestructure.projectspath.resolve()
        self.projectdir = file_dir
        self.current_item = None
        self.current_testinfo = None
        self.initUI()


    def initUI(self):

        ## LeftLayout
        leftLayout = QVBoxLayout()

        #leftLayout.setMaximumWidth(200)
        ### Image List
        self.testList = ImageFileList(testfs=self.testfs, parent=self)
        leftLayout.addWidget(self.testList)

        updateButton = QPushButton("Refresh")

        def refresh():
            self.testList.settestfs(self.testfs)
            importlib.reload(scilab)
            importlib.reload(scilab.expers.mechanical.fatigue)

        updateButton.clicked.connect(refresh)
        leftLayout.addWidget(updateButton)


        ## RightLayout
        rightLayout = QVBoxLayout()

        ## Test Info (text for now)
        self.testInfoPane = QTextEdit(self)
        self.testInfoPane.setReadOnly(True)
        self.testInfoPane.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoAll)

        ### QForms
#        self.formLayout = self._formlayout()

        ### ButtonLayout

        buttonLayout = QHBoxLayout()
        okButton = QPushButton("Run Image Dims")
        dataButton = QPushButton("Enter Data")
        cancelButton = QPushButton("Run Preconditions Fit")
        okButton.clicked.connect(self.run_image_dims)
        cancelButton.clicked.connect(self.run_preconditions)
        dataButton.clicked.connect(self.run_enterdata)

        buttonLayout.addWidget(dataButton)
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)

#        bottomRightPane = QHBoxLayout()
#        bottomRightPane.addWidget(self.dataform)
#        bottomRightPane.addStretch(1)

#        bottomRightPane.addWidget()
        rightLayout.addWidget(self.testInfoPane)
        # rightLayout.addStretch(1)
        # rightLayout.addWidget(okButton)
        # rightLayout.addWidget(okButton)
        rightLayout.addLayout(buttonLayout)


        mainPanel =  QSplitter(self)

        lFrame = QFrame(self)
        lFrame.setLayout(leftLayout)

        rFrame = QFrame(self)
        rFrame.setLayout(rightLayout)

        mainPanel.addWidget(lFrame)
        mainPanel.addWidget(rFrame)

        # mainPanel = QHBoxLayout()
        # mainPanel.addLayout(leftLayout)
        # mainPanel.addLayout(rightLayout)
        # mainPanel.addStretch(0.1)


        def on_test_item_changed(curr, prev):
            self.set_testinfo_panel(curr)

        self.testList.currentItemChanged.connect(on_test_item_changed)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(mainPanel)
        self.setLayout(mainLayout)

        self.setGeometry(300, 300, 600, 400)
        self.setWindowTitle('Project Tests: '+self.projectdir.name)
        self.show()

#    def _formlayout(self):
#
#        formdata = self._formdata = DataTree()
#
#        formLayout = QFormLayout()
#        formLayout.addRow(self.tr("&Name:"), nameLineEdit)
#        formLayout.addRow(self.tr("&Email:"), emailLineEdit)
#        formLayout.addRow(self.tr("&Age:"), ageSpinBox)
#
    def set_testinfo_panel(self, curr=None):

        debug(type(curr), repr(curr))
        self._test_measurements = DataTree(area="", min_area="", gauge="")

        item = self.testList.getitem(curr.text() if curr else None)
        self.current_item = item
        self.current_testinfo = TestInfo(name=item.name) if item else None

        self._infotext = self.get_testitem_info(self.current_item, self.current_testinfo)
        self.testInfoPane.setText(self._infotext)



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



def main():

    fs = FileStructure('fatigue failure (cycles, expr1)', 'cycles-expr2')
    # Test test images for now
    test_dir = fs.test_parent.resolve()

    debug(test_dir)

    app = QApplication(sys.argv)
    ex = Example(fs, test_dir)
    ex.show()

    sys.exit(app.exec_())



if __name__ == '__main__':


    from scilab.expers.mechanical.fatigue.cycles import FileStructure
    from scilab.expers.mechanical.fatigue.cycles import TestInfo as TestInfo

    main()