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
        
        self.settings = QSettings("Scilab", "Dataprocessor Gui")


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
        self.testpanel = TestPanelLayout(parent=self)
        
        lFrame = QFrame(self)
        lFrame.setLayout(self.testInfoPanel)

        # rFrame = QFrame(self)
        # rFrame.setLayout()

        # == Main Panel Init ==
        mainPanel =  QSplitter(self)
        mainPanel.addWidget(lFrame)
        mainPanel.addWidget(self.testpanel)

        self.testList.currentItemChanged.connect(self.testpanel.actionUpdateDetailPanel)

        mainLayout = QVBoxLayout()
        
        self.setCentralWidget(mainPanel)
        
        self.statusBar()

        openFile = QAction(QIcon.fromTheme('refresh.png'), 'Refresh', self)
        openFile.setShortcut('Ctrl+R')
        openFile.triggered.connect(self.testpanel.projectrefresh)
                
        mainToolbar = self.addToolBar("Main")
        mainToolbar.addAction(openFile)
        mainToolbar.addSeparator()
        mainToolbar.addWidget(self.dropdownfilebox(self.testpanel))

        self.setWindowTitle('Project Test DataProcessor')
        
        self.show()
    
    def dropdownfilebox(self, testpanel):
        
        layout = QHBoxLayout(self)
        button = QToolButton(self)
        button.setPopupMode(QToolButton.MenuButtonPopup)
        button.setMenu(QMenu(button))
        textBox = QTextBrowser(self)
        action = QWidgetAction(button)
        action.setDefaultWidget(textBox)
        button.menu().addAction(action)
        
        @Slot(str)
        def dropdownfilebox_update(projdir):
            ''' Give evidence that a bag was punched. '''
            print("Dropdown project dir update:", projdir)
            button.setText("{:<80s}".format(Path(str(projdir)).name))
        
        dropdownfilebox_update("Project Directory ... ")
        testpanel.projectdirchanged.connect(dropdownfilebox_update)
        button.clicked.connect(self.showFileDialog)
        return button

    def showFileDialog(self):
        fname = QFileDialog.getExistingDirectory(self, 'Choose Project Directory', '~/')
        debug(fname)
        # self.testpanel.projectdirchanged.emit(str(fname)+os.path.sep)
        self.testpanel.setprojdir(fname)

def main():

    app = QApplication(sys.argv)
    ex = DataProcessorGuiMain()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':


    # from scilab.expers.mechanical.fatigue.cycles import FileStructure
    # from scilab.expers.mechanical.fatigue.cycles import TestInfo as TestInfo

    main()