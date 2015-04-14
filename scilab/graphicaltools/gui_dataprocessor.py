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
from scilab.graphicaltools.gui_dataprocessor_testhandler import *


def supported_image_extensions():
    ''' Get the image file extensions that can be read. '''
    formats = QImageReader().supportedImageFormats()
    # Convert the QByteArrays to strings
    return [str(fmt) for fmt in formats]


class ExperTestList(QListWidget):

    def __init__(self, parent):
        super(ExperTestList, self).__init__(parent=parent)
        # self.settestfs(testfs)

    def _populate(self):
        ''' Fill the list with images from the
        current directory in self._dirpath. '''

        # In case we're repopulating, clear the list
        self.clear()

        testitemsd = self.testfs.testitemsd()

        # Order Tests by last modification time
        self._testitems = collections.OrderedDict(
                    sorted(
                        ( (str(name), test) for name, test in testitemsd.items() ),
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

class DataProcessorGuiMain(QMainWindow):

    def __init__(self):
        super().__init__()

        # self.testDetails = TestHandler()
        self.initUI()


    def infoTestInfoPanel(self):
        
        # == LeftLayout ==
        leftLayout = QVBoxLayout()

        # == TestInfo List ==
        self.testList = ExperTestList(parent=self)
        
        leftLayout.addWidget(self.testList)

        updateButton = QPushButton("Refresh")

        def actionRefresh():
            self.testList.settestfs(self.testfs)
            importlib.reload(scilab)
            importlib.reload(scilab.expers.mechanical.fatigue)

        updateButton.clicked.connect(actionRefresh)
        leftLayout.addWidget(updateButton)

        return leftLayout


    def initUI(self):

        # self.projectPanel = self.projectPanel()
        self.testInfoPanel = self.infoTestInfoPanel()
        self.testPanel = TestPanelLayout(parent=self)
        
        lFrame = QFrame(self)
        lFrame.setLayout(self.testInfoPanel)

        # rFrame = QFrame(self)
        # rFrame.setLayout()

        # == Main Panel Init ==
        mainPanel =  QSplitter(self)
        mainPanel.addWidget(lFrame)
        mainPanel.addWidget(self.testPanel)

        self.testList.currentItemChanged.connect(self.testPanel.actionUpdateDetailPanel)

        mainLayout = QVBoxLayout()
        
        self.setCentralWidget(mainPanel)
        
        
        self.statusBar()

        openFile = QAction(QIcon.fromTheme('open.png'), 'Open', self)
        openFile.setShortcut('Ctrl+O')
        openFile.setStatusTip('Open Project')
        openFile.triggered.connect(self.showFileDialog)

        # menubar = self.menuBar()
        # fileMenu = menubar.addMenu('&File')
        # fileMenu.addAction(openFile)
                
        mainToolbar = self.addToolBar("Main")
        mainToolbar.addAction(openFile)
        mainToolbar.addSeparator()
        mainToolbar.addWidget(self.dropdownfilebox())
        
        # layout.addWidget(self.button)
        
        
        # mainLayout.addWidget(mainPanel)
        # self.setLayout(mainLayout)

        # self.setGeometry(300, 300, 800, 640)
        self.setWindowTitle('Project Test DataProcessor')
        
        self.show()
    
    def dropdownfilebox(self):
        
        layout = QHBoxLayout(self)
        button = QToolButton(self)
        button.setPopupMode(QToolButton.MenuButtonPopup)
        button.setMenu(QMenu(button))
        button.setText("File...")
        textBox = QTextBrowser(self)
        action = QWidgetAction(button)
        action.setDefaultWidget(textBox)
        button.menu().addAction(action)
        
        return button
        

    def showFileDialog(self):

        fname, _ = QFileDialog.getOpenFileName(self, 'Open file', '~/')
        
        # f = open(fname, 'r')

        debug(fname)
        # with f:
            # data = f.read()
            # self.textEdit.setText(data)

def main():

    app = QApplication(sys.argv)
    ex = DataProcessorGuiMain()
    ex.show()

    sys.exit(app.exec_())



if __name__ == '__main__':


    # from scilab.expers.mechanical.fatigue.cycles import FileStructure
    # from scilab.expers.mechanical.fatigue.cycles import TestInfo as TestInfo

    main()