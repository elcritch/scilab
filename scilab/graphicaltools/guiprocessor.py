#!/usr/bin/env python3

# Import PySide classes
import sys, collections, json, tabulate

from PyQt5.QtCore import *
from PyQt5.QtGui import *
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

import scilab
from scilab.expers.configuration import FileStructure
from scilab.graphicaltools.gui_dataprocessor_testhandler import *
import scilab.graphicaltools.forms as forms


def supported_image_extensions():
    ''' Get the image file extensions that can be read. '''
    formats = QImageReader().supportedImageFormats()
    # Convert the QByteArrays to strings
    return [str(fmt) for fmt in formats]

class BasicHub(QObject):
 
    def __init__(self):
        super().__init__()
 
    @Slot(str)
    def display(self, config):
        print(config)
        self.on_client_event.emit("Howdy!")
 
    @Slot(str)
    def disconnect(self, config):
        print(config)
 
    on_client_event = Signal(str)
    on_actor_event = Signal(str)
    on_connect = Signal(str)
    on_disconnect = Signal(str)


class BasicWebView(QWebView):
    
    def __init__(self):
        super().__init__()
        
        # self.baseHtml = Path(__file__).parent / "www" / "basic.html"
        self.hub = BasicHub()
        
    def init(self):
        self.loadFinished.connect(self.onLoad)
        # self.load(self.baseHtml.as_posix())
        # self.setHtml("<html><h1>Test</h1></html>")
        self.show()
    
    def onLoad(self):
                
        # This is the body of a web browser tab
        self.page().settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
        
        # This is the actual context/frame a webpage is running in.
        # Other frames could include iframes or such.
        self.myFrame = self.page().mainFrame()
        
        # ATTENTION here's the magic that sets a bridge between Python to HTML
        self.myFrame.addToJavaScriptWindowObject("hub", self.hub)
        
        # Tell the HTML side, we are open for business
        self.myFrame.evaluateJavaScript("ApplicationIsReady()")


class ExperTestList(QListWidget):

    def __init__(self, parent):
        super(ExperTestList, self).__init__(parent=parent)
        # self.settestfs(testfs)
        self.parent = parent
        self.currentItemChanged.connect(self.updateTestItem)

    def _populate(self):
        ''' Fill the list with images from the
        current directory in self._dirpath. '''

        # In case we're repopulating, clear the list
        self.clear()

        testitemsd = self.testfs.testitemsd()

        # Order Tests by last modification time
        self._testitems = collections.OrderedDict(
                    reversed(sorted(
                        ( (test.short, DataTree(folder=folder, test=test)) for test, folder in testitemsd.items() ),
                        key=lambda f: f[1].folder.stat().st_mtime
                    )))

        print("Setting testfolders:", len(self._testitems))

        for key, value in self._testitems.items():
            item = QListWidgetItem(self)
            item.setText(key)
        
        if len(self._testitems) > 0:
            self.setCurrentRow(0)

    def updateTestItem(self, curr=None, prev=None):
        item = self.getitem(curr.text() if curr else None)
        self.current_item = item
        self.parent.starttestitemchanged.emit(item)
    
    def getitem(self, text):
        return self._testitems.get(text, None)

    def settestfs(self, testfs):
        ''' Set the current image directory and refresh the list. '''
        self.testfs = testfs
        self._populate()

import importlib

class DataProcessorView(QTextEdit):
    
    def __init__(self):
        super(DataProcessorView, self).__init__()
        
        self.setReadOnly(True)
        
    
    def init(self):
        
        pass
        
        
        # self.setContent("<html><h1>Text:</h1></html>", "text/html", QUrl("./"))
        
    
class TestPageWebView(BasicWebView):
    
    def __init__(self):
        super(TestPageWebView, self).__init__()
    
    def init(self):
        
        self.setContent("<html>Test!</html>", "text/html", QUrl("./"))

class TestProtocolView(QFrame):
    
    def __init__(self, parent):
        super(TestProtocolView, self).__init__()
        self.parent = parent
        self.setFrameStyle(QFrame.StyledPanel)
        self.protocolView = BasicWebView()
        
        layout = QVBoxLayout()
        layout.addWidget(self.protocolView)
        self.setLayout(layout)

    def setHtml(testhtml, testqurl):
        self.protocolView.setHtml(testhtml, testqurl)
        
    @Slot(object)
    def update(self, obj):
        
        print("TestProtocolView", obj)
        test = self.parent.tester.getitem()
        
        if not test["folder",]:
            self.protocolView.setHtml("<html></html>", QUrl())
            
        else:
            protocolUrl = test.folder.main / ".." / ".." / 'protocol.html'
        
            if not protocolUrl.exists():
                logging.warn("Protocol doesn't exist for test: "+str(protocolUrl))
                return 
            
            with protocolUrl.open('rb') as protocolFile:            
                protocolHtmlStr = protocolFile.read().decode(encoding='UTF-8')
        
                self.protocolView.setHtml(protocolHtmlStr, QUrl("."))
        
            # self.testitemchanged.connect(lambda obj: setitem(obj) )
        

class DataProcessorGuiMain(QMainWindow):

    starttestitemchanged = Signal(object)
    testitemchanged = Signal(object)

    def __init__(self):
        super().__init__()
        self.settings = QSettings("Scilab", "Dataprocessor Gui")
        self.initUI()

    def infoTestInfoPanel(self):
        
        # == LeftLayout ==
        leftLayout = QVBoxLayout()

        # == TestInfo List ==
        self.testList = ExperTestList(parent=self)
        
        # self.testList.currentItemChanged.connect(lambda c, p: self.testitemchanged.emit(c))
        
        leftLayout.addWidget(self.testList)

        updateButton = QPushButton("Refresh")
        updateButton.clicked.connect(lambda: self.tester.projectrefresh.emit())
        leftLayout.addWidget(updateButton)
        
        createButton = QPushButton("Create")
        createButton.clicked.connect(lambda: self.tester.createnewtest.emit())
        leftLayout.addWidget(createButton)

        self.tester.projectrefresh.connect(self.testlistRefresh)
        
        return leftLayout

    @Slot()
    def testlistRefresh(self):
        print("testlistRefresh")
        self.testList.settestfs(self.tester.fs)

    def initDataProcessorWidget(self):
        
        widget = QWidget()
        
        self.dataProcessorOutput = DataProcessorView()
        
        self.dataProcessorRun = QPushButton("Execute")
        self.dataProcessorRun.clicked.connect(lambda: self.tester.processtest.emit())
        
        self.dataProcessorImportRaw = QPushButton("Import Raw Files")
        self.dataProcessorImportRaw.clicked.connect(lambda: self.tester.processtestimport.emit())
        
        h12	= QHBoxLayout()
        h12.addStretch(stretch=100)
        h12.addWidget(self.dataProcessorImportRaw)
        h12.addWidget(self.dataProcessorRun)
        
        q12 = QWidget()
        q12.setLayout(h12)
        
        v1	= QVBoxLayout()
        v1.addWidget(self.dataProcessorOutput)
        v1.addWidget(q12)
        
        widget.setLayout(v1)
        
        self.dataProcessorOutput.init()
        self.testitemchanged.connect(lambda x: print("Item changed!", type(x), x))
        self.testitemchanged.connect(lambda: self.tester.processtestclear.emit())
        
        def initDataProcessorWidget_append(html):
            html = html.replace("\n", "<br>\n")
            self.dataProcessorOutput.moveCursor(QTextCursor.End)
            self.dataProcessorOutput.insertHtml(html)
        
        self.tester.processtestupdate.connect(initDataProcessorWidget_append)
        self.tester.processtestclear.connect(self.dataProcessorOutput.clear)
        
        return widget
    
    def initTestPageWebView(self):
        
        widget = QWidget()
        
        self.testPageWebView = TestPageWebView()

        v1    = QVBoxLayout()
        v1.addWidget(self.testPageWebView)        
        widget.setLayout(v1)
        
        self.testPageWebView.init()
        
        def setitem(testobj):
            # set testfolder item
            self.tester.setitem(testobj)
            
            # set
            if testobj:
                testhtml, testurl = self.tester.getinfopanelhtml(testobj)
                testqurl = QUrl("file://{}/".format(testurl.resolve()))
                print("Test URL:", testqurl)
                self.testPageWebView.setHtml(testhtml, testqurl)
            else:
                self.testPageWebView.setHtml("<html></html>", QUrl())
        
        self.testitemchanged.connect(lambda obj: setitem(obj) )
        
        return widget
        
    def initTestDataWebView(self):
        
        widget = QWidget()
        webView = TestPageWebView()
        
        v1 = QVBoxLayout()
        v1.addWidget(webView)        
        widget.setLayout(v1)
        
        webView.init()
        
        def setitem(testobj):

            if testobj:
                test = self.tester.getitem()
                # debug(test.folder.details)
                
                tables = []                
                details = Json.load_json_from(test.folder.details, defaultHandler=True)
                debug(list(details.keys()))
                for key in details.keys():
                    if not isinstance(details[key], collections.Mapping):
                        tables.append("<h1>{}</h1><br>\n{}".format(key, str(details[key])))
                    else:
                        fdetails = sorted([ (k,v) for k,v in flatten(details[key]).items() ])
                        fdtable = tabulate.tabulate(fdetails, headers=["Key", "Value"], tablefmt="html")
                    
                        tables.append("<h2>{}</h2><br>\n\n{}".format(key, str(fdtable)))
                
                webView.setHtml("# JSON Calculations:\n\n{fdtable}".format(fdtable="<br>\n<br>\n".join(tables)))
            else:
                webView.setHtml("<html></html>", QUrl())
        
        self.testitemchanged.connect(lambda obj: setitem(obj) )
        
        self.testDataWebView = webView
        
        return widget
    
    @Slot(object)
    def updateTestItem(self, item):
        self.tester.setitem(item)
        self.testitemchanged.emit(item)
        
    def initUI(self):

        self.tester = TestHandler(self)
        
        self.starttestitemchanged.connect(self.updateTestItem)
        
        self.testPanelTabs = QTabWidget(self)
        self.testPanelTabs.addTab(self.initTestPageWebView(), "Test Sample Panel")
        self.testPanelTabs.addTab(self.initTestDataWebView(), "Test Sample Data")
        self.testPanelTabs.addTab(self.initDataProcessorWidget(), "Data Processor")
        
        self.testInfoPanel = self.infoTestInfoPanel()
        self.testProtocolView = TestProtocolView(self)
        self.testitemchanged.connect(self.testProtocolView.update)
        
        lFrame = QFrame(self)
        lFrame.setLayout(self.testInfoPanel)

        self.testSplitter = QSplitter(self)
        self.testSplitter.addWidget(self.testProtocolView)
        self.testSplitter.addWidget(self.testPanelTabs)
        self.testLabel = QLabel("<h2>Test:</h2> ")


        testPanelsLayout = QVBoxLayout()
        testPanelsLayout.addWidget(self.testLabel)
        testPanelsLayout.addWidget(self.testSplitter)
        
        self.testPanels = QFrame(self)
        self.testPanels.setLayout(testPanelsLayout)
        
        # == Main Panel Init ==
        mainPanel = QSplitter(self)
        mainPanel.addWidget(lFrame)
        mainPanel.addWidget(self.testPanels)
        
        mainLayout = QVBoxLayout()
        
        self.setCentralWidget(mainPanel)
        
        self.statusBar()

        refresh = QAction(QIcon.fromTheme('refresh.png'), 'Refresh', self)
        refresh.setShortcut('Ctrl+R')
        refresh.triggered.connect(lambda: self.tester.projectrefresh.emit())
        
        mainToolbar = self.addToolBar("Main")
        mainToolbar.addAction(refresh)
        mainToolbar.addSeparator()
        
        dropdown, openfile = self.dropdownfilebox(self.tester)
        mainToolbar.addWidget(dropdown)
        mainToolbar.addAction(openfile)

        self.setWindowTitle('Project Test DataProcessor')
        
        self.show()
    
    def dropdownfilebox(self, tester):
        
        def getfiledialogdir():
            return json.loads(self.settings.value("dropdownfilebox/previousprojs", "[]"))
            
        filedialogdir = getfiledialogdir()
        
        combobox = QComboBox(self)
        combobox.setEditable(True)
        combobox.addItems(getfiledialogdir())
        combobox.setEditText("")
        combobox.setCurrentIndex(-1)
        
        @Slot(str)
        def dropdownfilebox_history(projdir):
            # update dropdown box
            previousprojs = [ combobox.itemText(idx) for idx in range(combobox.count()) ]
            
            if projdir in previousprojs: 
                idx = previousprojs.index(projdir)
                combobox.setCurrentIndex(idx)
            else:
                previousprojs.insert(0,str(projdir))
                combobox.insertItem(0,str(projdir))
                combobox.setCurrentIndex(0)
                
                print("Dropdown project history update:", previousprojs)
                self.settings.setValue("dropdownfilebox/previousprojs", json.dumps(previousprojs))
            
            combobox.setEditText( Path(projdir).name )
            self.tester.projectrefresh.emit()
            
        
        @Slot(int)
        def dropdownfilebox_selected(idx):
            debug("dropdownfilebox_selected", idx)
            projdir = combobox.itemText(idx)
            tester.setprojdir(projdir)
            
        combobox.activated.connect(dropdownfilebox_selected)
        tester.projectdirchanged.connect(dropdownfilebox_history)
        
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
        self.tester.setprojdir(fname)

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