#!/usr/bin/env python3

# Import PySide classes
import sys, collections, logging, traceback, io, multiprocessing, copy, time

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import QWebView
from PyQt5.QtWebKit import QWebSettings
from PyQt5.QtNetwork import QNetworkRequest

Signal = pyqtSignal
Slot = pyqtSlot

from scilab.tools.project import *
from scilab.tools import testingtools

from pathlib import *
# from fn import _ as __
# import formlayout
# import boltons.tbutils

import scilab
from scilab.expers.configuration import FileStructure
# from scilab.expers.mechanical.fatigue.cycles import TestInfo as TestInfo
# from scilab.expers.mechanical.fatigue.helpers import *
import scilab.tools.jsonutils as Json
from scilab.graphicaltools.multifile import *
from scilab.datahandling.datahandlers import *
import scilab.graphicaltools.forms as forms
import scilab.datahandling.dataprocessor as dataprocessor

import numpy as np

import scilab.expers.configuration as config
from scilab.expers.configuration import BasicTestInfo

def _process_test(processargs):
    
    testinfodict, fs, args, queues = processargs
    
    sys.stdout, a = queues
    
    # print("processing!!!", file=stdoutprev)
    for i in range(60):
        print("{execute! %d}"%i)
        time.sleep(.1)

    
def __process(processargs):
    
    print("### Processing ")
    testinfodict, fs, args, queues = processargs
    sys.stdout, sys.stderr = queues
    
    print("### Processing (stdout) ")
    
    # fs = config.FileStructure(projdescpath=projdescpath,verify=True)
    TestInfo = generatetestinfoclass(**fs.projdesc["experiment_config"]["testinfo"])
    testinfo = TestInfo(**testinfodict)
    debug(testinfo)
    
    test = DataTree()
    test.data = DataTree()
    test.info = testinfo
    test.folder = fs.testfolder(testinfo=test.info, ensure_folders_exists=False)
    
    debug(list(test.keys()), fs, args)

    expertype = fs.projdesc["experiment_config"]["type"]

    if expertype == "cycles":
        import scilab.expers.mechanical.fatigue.cycles as exper
    elif expertype == "uts":
        import scilab.expers.mechanical.fatigue.uts as exper
    else:
        raise ValueError("Do not know how to process test type.", expertype)
    
    args.parser_data_sheet_excel = exper.parser_data_sheet_excel
    args.parser_image_measurements = exper.parser_image_measurements
    args.codehandlers = exper.getcodehandlers()


    if not fs or not test or not args:
        debug(fs, test, args)
        logging.warning("Cannot execute test! Empty arguments ")
        return

    if not 'data' in test:
        test.data = DataTree()
        
    dataprocessor.execute(fs=fs, name=test.info.name, testconf=test, args=args )

    print("Done")

def _process(processargs):
    try:
        __process(processargs)
    except Exception as err:
        print("[Error]", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        raise err
    finally:
        print("[Finished]")

class ProjectContainer():
    
    projectdirchanged = Signal(str)
    projectrefresh = Signal()
    createnewtest = Signal()
    processtest = Signal()
    processtestupdate = Signal(str)
    
    def __init__(self, poolsize=4):
        
        self.fs         = None
        self.test_dir   = None
        self.testitemsd = None
        self.args       = None  
        self.projectdesc = None
        self.test = DataTree()
        self.pool = multiprocessing.Pool(processes=poolsize)
        
        self.createnewtest.connect(self.docreatenewtest)
        self.processtest.connect(self.doprocesstest)
    
    def showErrorMessage(self, errmsg, ex=None):
        errorfmt = "Invalid project:<br>Error `{errmsg}`"
        if ex: 
            errorfmt += "<br>Exception:<br><pre><code>{ex}</code></pre>"
        errorMessageDialog = QErrorMessage(self._parent)
        errorMessageDialog.showMessage(errorfmt.format(errmsg=errmsg, ex=str(ex)))
    
    @Slot()
    def doprocessorupdate(self):
        stdout, stderr = self.test.queues[0].getvalue(wait=False), self.test.queues[1].getvalue(wait=False)
        print(stdout, flush=True, end='', file=sys.stdout)
        print(stderr, flush=True, end='', file=sys.stderr)
        
        if len(stdout) > 0:
            self.processtestupdate.emit(stdout.rstrip())
        if len(stderr) > 0:
            self.processtestupdate.emit(stderr.rstrip())

    @Slot()
    def doprocesstest(self):
        
        print("processtest!!")
        testinfodict = { str(k): str(v) for k,v in self.test.info._asdict().items() }
        debug(testinfodict)
        # debug(self.fs)

        shallowfs = copy.copy(self.fs)
        shallowfs._testinfo = None

        self.test.queue = multiprocessing.Queue()
        self.test.timer = QTimer(self._parent)
        self.test.timer.timeout.connect(self.doprocessorupdate)
        
        self.test.timer.start(1000)
        self.test.queues = MultiProcessFile(), MultiProcessFile()
        
        print("starting queue: ", self.test.queues[0])
        processargs = testinfodict, shallowfs, self.args, self.test.queues
        
        # self.pool.map_async(_process_test, [processargs])
        self.pool.map_async(_process, [processargs])
        
    @Slot()
    def docreatenewtest(self):
        
        def getvalues():
            return json.loads(self._parent.settings.value("dialog/createdialog", "{}"))
        def setvalues(values):
            self._parent.settings.setValue("dialog/createdialog", json.dumps(values))
        
        TestInfo = self.fs._testinfo
        
        fieldnames = TestInfo._fields
        regexes = TestInfo._regexfields
        
        priorvalues = getvalues()
        fielddata = [ ("<b>%s</b> [<i>%s</i>]"%(name, regexes[name].pattern), priorvalues.get(name,"")) 
                        for name in fieldnames ]
        
        datalist = forms.fedit(fielddata)
        debug(datalist)
        
        if not fielddata:
            return 
        
        datadict = DataTree({ k:v for k,v in zip(fieldnames, datalist) })
        
        setvalues(datadict)
        
        try:
            debug(datadict)

            ti = TestInfo(**TestInfo.createfields(valuedict=datadict))
            
            print(repr(ti))
            
            tf = self.fs.makenewfolder(**ti._asdict())
            
            self.projectrefresh.emit()
            
            # TODO: emit testitem changed with new test name?
            self._parent.testitemchanged.emit(DataTree(folder=tf.main, test=ti))
            
        except Exception as err:
            logging.exception(err)
            self.showErrorMessage("Error parsing: ", 
                                    ex=traceback.format_exc())
            raise err
                    
        
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


            args = DataTree()
            args.forceRuns = DataTree(raw=False, norm=True)
            args.version = "0"
            # args["force", "imagecropping"] = True
            # args["dbg","image_measurement"] = True
            # === Excel === 
            args.options = DataTree()
            args.options["output", "excel"] = False
            args.options["output", "onlyVars"] = True
            
            self.args = args
            print("Setting args: ", self.args)
            
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
        
        if not item:
            self.test = DataTree()
        else:
            self.test = DataTree()
            self.test.info = item.test
            self.test.folder = self.fs.testfolder(testinfo=self.test.info, ensure_folders_exists=False)

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


