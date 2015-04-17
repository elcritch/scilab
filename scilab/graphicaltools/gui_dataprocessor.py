#!/usr/bin/env python3

# Import PySide classes
import sys, collections, json
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
        self.settings = QSettings("Scilab", "Dataprocessor Gui")
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

        refresh = QAction(QIcon.fromTheme('refresh.png'), 'Refresh', self)
        refresh.setShortcut('Ctrl+R')
        refresh.triggered.connect(self.testpanel.projectrefresh)
                
        
        mainToolbar = self.addToolBar("Main")
        mainToolbar.addAction(refresh)
        mainToolbar.addSeparator()
        
        dropdown, openfile = self.dropdownfilebox(self.testpanel)
        mainToolbar.addWidget(dropdown)
        mainToolbar.addAction(openfile)

        self.setWindowTitle('Project Test DataProcessor')
        
        self.show()
    
    def dropdownfilebox(self, testpanel):
        
        def getfiledialogdir():
            return json.loads(self.settings.value("dropdownfilebox/previousprojs", "[]"))
            
        filedialogdir = getfiledialogdir()
        
        combobox = QComboBox(self)
        combobox.setEditable(True)
        combobox.addItems(getfiledialogdir())
        combobox.setEditText("")
        
        @Slot(str)
        def dropdownfilebox_history(projdir):
            # update dropdown box
            previousprojs = [ combobox.itemText(idx) for idx in range(combobox.count()) ]
            
            if projdir in previousprojs: 
                idx = previousprojs.index(projdir)
                combobox.setCurrentIndex(0)
            else:
                previousprojs.insert(0,str(projdir))
                combobox.insertItem(0,str(projdir))
                combobox.setCurrentIndex(0)
                
                print("Dropdown project history update:", previousprojs)
                self.settings.setValue("dropdownfilebox/previousprojs", json.dumps(previousprojs))
            
            combobox.setEditText( Path(projdir).name )
        
        @Slot(int)
        def dropdownfilebox_selected(idx):
            debug("dropdownfilebox_selected", idx)
            projdir = combobox.itemText(idx)
            self.testpanel.setprojdir(projdir)
            
        combobox.activated.connect(dropdownfilebox_selected)
        testpanel.projectdirchanged.connect(dropdownfilebox_history)
        
        openfile = QAction(QIcon.fromTheme('open.png'), 'Open', self)
        openfile.setShortcut('Ctrl+O')
        openfile.triggered.connect(self.showFileDialog)
        
        # button.clicked.connect(self.showFileDialog)
        # return button
        return combobox, openfile

    def showFileDialog(self):
        filedialogdir = self.settings.value("dropdownfilebox/filedialogdir", os.path.expanduser("~/"))
        debug(filedialogdir)
        
        fname = QFileDialog.getExistingDirectory(self, 'Choose Project Directory', filedialogdir)
        if not fname:
            return
            
        debug(fname)
        self.settings.setValue("dropdownfilebox/filedialogdir", fname)
        self.testpanel.setprojdir(fname)

def main():

    app = QApplication(sys.argv)
    ex = DataProcessorGuiMain()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':


    # from scilab.expers.mechanical.fatigue.cycles import FileStructure
    # from scilab.expers.mechanical.fatigue.cycles import TestInfo as TestInfo
        # button = QToolButton(self)
        # button.setPopupMode(QToolButton.MenuButtonPopup)
        # button.setMenu(QMenu(button))
        # action = QWidgetAction(button)
        # action.setDefaultWidget(combobox)
        # button.menu().addAction(action)

    main()