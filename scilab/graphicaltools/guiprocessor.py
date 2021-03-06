#!/usr/local/bin/python3

# Import PySide classes
import sys, collections, json, tabulate, shutil

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import QWebView
from PyQt5.QtWebKit import QWebSettings
from PyQt5.QtNetwork import QNetworkRequest
from PyQt5.QtPrintSupport import QPrinter

Signal = pyqtSignal
Slot = pyqtSlot

import matplotlib
matplotlib.use('Agg')


from scilab.tools.project import *
from pathlib import *
# from fn import _ as __
# import formlayout

import scilab
from scilab.expers.configuration import FileStructure
from scilab.graphicaltools.guitesthandler import *
import scilab.graphicaltools.forms as forms
import scilab.datahandling.processingreports 

defaultCss = scilab.datahandling.processingreports.defaultCss 

def formatHtmlBlock(html_raw):
    return "\n".join([ l.strip() for l in html_raw.split("\n") ] )

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

        def keyerModTime(x):
            return -x[1].folder.stat().st_mtime

        def keyerName(x):
            return str(x[1].test.short)

        def keyerDate(x):
            months = [ "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec" ]
            dtstr = str(x[1].test.date)
            for idx, month in enumerate(months):
                dtstr = dtstr.replace(month, str(idx*10000))
            print("dtstr",dtstr)
            return -int(dtstr)
        
        self.sortKeyers = {
            "ModTime": keyerModTime,
            "Name": keyerName,
            "DateRun": keyerDate,
        }
        
        self.sortKeyer = self.sortKeyers["ModTime"]
        
    def setSortKey(self, name):        
        if name in self.sortKeyers.keys():
            print("Setting Sort Method:", name)
            self.sortKeyer = self.sortKeyers[name]
        else:
            print("Warning::No such sort method", name)

    def _populate(self):
        ''' Fill the list with images from the
        current directory in self._dirpath. '''

        # In case we're repopulating, clear the list
        self.clear()
        testitemsd = self.testfs.testitemsd()
                
        # Order Tests by last modification time
        self._testitems = collections.OrderedDict(
                    sorted( 
                        ([ "%s (%s)"%( test.short, test.date ), # Visible Key
                           DataTree(folder=folder, test=test) # Item Data
                         ] for test, folder in testitemsd.items()
                        )
                        , key=self.sortKeyer                        
                    )
                )

        print("Setting testfolders:", len(self._testitems))

        for key, value in self._testitems.items():
            item = QListWidgetItem(self)
            item.setText(key)
            item.setToolTip(value.test.name)
            ttfont = QFont("Monospace")
            ttfont.setStyleHint(QFont.TypeWriter)
            ttfont.setPointSize(9)
            item.setFont(ttfont)
            
            # item.setData( Qt.UserRole, key)
        
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
        
# class CustomStyle(QProxyStyle):
#
#     def drawControl(self, element, option, painter, widget):
#         if (element == QStyle.CE_CheckBox and option.styleObject):
#             option.styleObject.setProperty("_q_no_animation", true)
#         QProxyStyle.drawControl(element, option, painter, widget)

    
class TestPageWebView(BasicWebView):
    
    def __init__(self):
        super(TestPageWebView, self).__init__()
    
    def init(self):
        
        self.setContent("<html></html>".encode("ascii"), "text/html", QUrl("./"))

class TestProtocolView(QFrame):
    
    def __init__(self, parent):
        super(TestProtocolView, self).__init__()
        self.parent = parent
        self.setFrameStyle(QFrame.StyledPanel)
        self.protocolView = QWebView()
        
        self.protocolView.setStyle(QStyleFactory.create("windows"))
        
        layout = QVBoxLayout()
        layout.addWidget(self.protocolView)
        self.setLayout(layout)
        
        self.protocolView.page().mainFrame().javaScriptWindowObjectCleared.connect(self.populateJavaScriptWindowObject)
        self.protocolView.page().settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
        # view->page()->settings()->setAttribute(QWebSettings::DeveloperExtrasEnabled, true);
        

    @Slot()
    def populateJavaScriptWindowObject(self):
        self.protocolView.page().mainFrame().addToJavaScriptWindowObject("formExtractor", self);

    def setHtml(testhtml, testqurl):
        self.protocolView.setHtml(testhtml, testqurl)
        
    @Slot()
    def submit(self):
        
        try:

            frame = self.protocolView.page().mainFrame()
            updatedHtml = frame.toHtml()
            
            with self.protocolTestSampleUrl.open('w', encoding='utf-8') as protocolHtml:
                print("Saving updated protocol: ", str(self.protocolTestSampleUrl))
                protocolHtml.write(updatedHtml)
        
        finally:
            return False

        
    @Slot(object)
    def update(self, obj):
        
        print("TestProtocolView", obj)
        test = self.parent.tester.getitem()
        
        if not test["folder",]:
            self.protocolView.setHtml("<html></html>", QUrl())
            
        else:
            protocolUrl = test.folder.main / ".." / ".." / 'protocol.html'
            protocolTestSampleUrl = test.folder.main / 'protocol (test={}).html'.format(test["info"].short)
            
            self.protocolTestSampleUrl = protocolTestSampleUrl
            
            if not protocolUrl.exists() and not protocolTestSampleUrl.exists():
                logging.warn("Protocol doesn't exist for test: "+str(protocolUrl))
                return 
            
            if not protocolTestSampleUrl.exists():
                shutil.copy(str(protocolUrl), str(protocolTestSampleUrl))
                
            with protocolTestSampleUrl.open('rb') as protocolFile:            
                protocolHtmlStr = protocolFile.read().decode(encoding='UTF-8')
                self.protocolView.setHtml(protocolHtmlStr, QUrl("."))            
        

class DataProcessorGuiMain(QMainWindow):

    starttestitemchanged = Signal(object)
    testitemchanged = Signal(object)

    def __init__(self):
        super().__init__()
        self.settings = QSettings("Scilab", "Dataprocessor Gui")
        self.initUI()
        self.__current_item = None

    def infoTestInfoPanel(self):
        
        # == LeftLayout ==
        leftLayout = QVBoxLayout()

        # == TestInfo List ==
        self.testList = ExperTestList(parent=self)
        
        # self.testList.currentItemChanged.connect(lambda c, p: self.testitemchanged.emit(c))
        
        leftLayout.addWidget(self.testList)

        # Sort Combo Box
        def updateSorter(keyText):
            self.testList.setSortKey(keyText)
            self.tester.projectrefresh.emit()
            
        combo = QComboBox(self)
        combo.addItem("–")
        [ combo.addItem(keyerName) for keyerName in sorted(self.testList.sortKeyers.keys()) ]
        combo.activated[str].connect(updateSorter)
        leftLayout.addWidget(combo)
        
        # Refresh Test Lists
        updateButton = QPushButton("Refresh")
        updateButton.clicked.connect(lambda: self.tester.projectrefresh.emit())
        leftLayout.addWidget(updateButton)
        
        # Create New Test
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
        
        self.dataOptions = QPushButton("Options")
        self.dataOptions.clicked.connect(self.tester.getargs)
        
        self.dataProcessorRun = QPushButton("Execute")
        self.dataProcessorRun.clicked.connect(lambda: self.tester.processtest.emit())
        
        self.dataProcessorImportRaw = QPushButton("Import Raw Files")
        self.dataProcessorImportRaw.clicked.connect(lambda: self.tester.processtestimport.emit())
        
        h12	= QHBoxLayout()
        h12.addStretch(stretch=100)
        h12.addWidget(self.dataOptions)
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
            htmlFmt = """
            <div style='white-space: pre; font-family: "Courier New", Courier, monospace; font-size: 10; '> 
            {}
            </div>
            <br>\n
            """
            
            self.dataProcessorOutput.moveCursor(QTextCursor.End)
            self.dataProcessorOutput.insertHtml(formatHtmlBlock(htmlFmt).format(html))
            self.dataProcessorOutput.moveCursor(QTextCursor.End)
        
        self.tester.processtestupdate.connect(initDataProcessorWidget_append)
        self.tester.processtestclear.connect(self.dataProcessorOutput.clear)
        
        return widget
    
    def initTestPageWebView(self):
        
        widget = QWidget()
        
        self.testPageWebView = TestPageWebView()
        refreshButton = QPushButton("Refresh")
        pdfButton = QPushButton("Save PDF")

        buttons = QWidget()
        h2 = QHBoxLayout()
        h2.addWidget(pdfButton)        
        h2.addWidget(refreshButton)     
        h2.setSizeConstraint(QLayout.SetFixedSize)
        buttons.setLayout(h2)        

        v1 = QVBoxLayout()
        v1.addWidget(self.testPageWebView)        
        v1.addWidget(buttons)     
        widget.setLayout(v1)
        
        self.testPageWebView.init()
        
        def setitem(testobj):
            # set testfolder item
            self.tester.setitem(testobj)
            
            # set
            if testobj:
                testhtml, testurl, testhtmlpath = self.tester.getinfopanelhtml(testobj)
                
                if testhtmlpath:
                    self._testhtmlpathpdf = testhtmlpath.with_suffix(".pdf")
                    self.printer.setOutputFileName(str(self._testhtmlpathpdf))
                    
                testqurl = QUrl("file://{}/".format(testurl.resolve()))
                self.testPageWebView.setHtml(testhtml, testqurl)
                    
                
            else:
                self.testPageWebView.setHtml("<html></html>", QUrl())
        
        # Connect Buttons
        self.testitemchanged.connect(lambda obj: setitem(obj) )
        refreshButton.clicked.connect(lambda obj: setitem(self.__current_item) )
        
        ## Save PDF Button
        self.printer = QPrinter()
        self.printer.setPageSize(QPrinter.A4)
        self.printer.setOutputFormat(QPrinter.PdfFormat)
 
        def savePdf():
            self.testPageWebView.print_(self.printer)
            
            msg = "PDF Saved: "+str(self._testhtmlpathpdf)
            print(msg)
            QMessageBox.information(self,"Information",msg)        
        
        pdfButton.clicked.connect(savePdf)
        
        return widget
        
    def initTestDataWebView(self):
        
        widget = QWidget()
        webView = TestPageWebView()
        
        refreshButton = QPushButton("Refresh")
        
        v1 = QVBoxLayout()
        v1.addWidget(webView)        
        v1.addWidget(refreshButton)     
        widget.setLayout(v1)
        
        ttfont = QFont("Monospace")
        ttfont.setStyleHint(QFont.TypeWriter)
        ttfont.setPointSize(8)
        webView.setFont(ttfont)
        webView.init()
        
        def setitem(testobj):

            if testobj:
                test = self.tester.getitem()
                # debug(test.folder.details)
                
                tables = []
                debug(test.folder.details) 
                details = Json.load_json_from(test.folder.details, defaultHandler=True)
                
                if not details:
                    webView.setHtml("<html></html>", QUrl())
                    return
                
                for key in details.keys():
                    if not isinstance(details[key], collections.Mapping):
                        tables.append("<h1>{}</h1><br>\n{}".format(key, str(details[key])))
                    else:
                        fdetails = sorted([ (k,v) for k,v in flatten(details[key]).items() ])
                        fdtable = tabulate.tabulate(fdetails, headers=["Key", "Value"], tablefmt="html")
                    
                        tables.append("<h2>{}</h2><br>\n\n{}".format(key, str(fdtable)))
                
                allfiles = [ [ f.relative_to(test.folder.main).as_posix(), ] for f in test.folder.main.rglob("**/*") ]
                allfilesTable = tabulate.tabulate( allfiles, headers=["All Files"], tablefmt="html")
                
                htmlFmt = """
                <style type="text/css">/*
                {defaultCss}
                </style>
                
                <div style='white-space: pre; font-family: "Courier New", Courier, monospace; font-size: 10; '> 
                # JSON Calculations:

                {fdtable}

                
                # All Files
                
                <br>
                
                {allfilesTable}
                
                </div>
                <br>
                """                
                webView.setHtml(formatHtmlBlock(htmlFmt).format(allfilesTable=allfilesTable,defaultCss=defaultCss, fdtable="<br>\n<br>\n".join(tables)))
            else:
                webView.setHtml("<html></html>", QUrl())
        
        def safe_setitem(testobj):
            try:
                setitem(testobj)
            except Exception as err:
                print(err.encoding("utf-8"))
        
        self.testitemchanged.connect(lambda obj: safe_setitem(obj) )
        refreshButton.clicked.connect(lambda obj: safe_setitem(self.__current_item) )
        
        self.testDataWebView = webView
        
        return widget
    
    @Slot(object)
    def updateTestItem(self, item):
        
        self.__current_item = item # probably not thread-safe
        self.tester.setitem(item)
        self.testitemchanged.emit(item)
        
    def initUI(self):

        self.tester = TestHandler(self)
        
        self.starttestitemchanged.connect(self.updateTestItem)
        
        self.testPanelTabs = QTabWidget(self)
        self.testPanelTabs.addTab(self.initDataProcessorWidget(), "Data Processor")
        self.testPanelTabs.addTab(self.initTestPageWebView(), "Summary Report")
        self.testPanelTabs.addTab(self.initTestDataWebView(), "Variables / Data")
        
        self.testInfoPanel = self.infoTestInfoPanel()
        self.testProtocolView = TestProtocolView(self)
        self.testitemchanged.connect(self.testProtocolView.update)
        
        lFrame = QFrame(self)
        lFrame.setLayout(self.testInfoPanel)

        # self.testProtocolView.setWidgetResizable(True)
        # self.testPanelTabs.setWidgetResizable(True)

        self.testSplitter = QSplitter(self)
        self.testSplitter.addWidget(self.testProtocolView)
        self.testSplitter.addWidget(self.testPanelTabs)
        # self.testLabel.setWidgetResizable(False)
        self.testSplitter.setStretchFactor(0, 1)
        self.testSplitter.setStretchFactor(1, 2)

        # self.testSplitter.setWidgetResizable(True)
        testPanelsLayout = QVBoxLayout()
        # testPanelsLayout.addWidget(self.testLabel)
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