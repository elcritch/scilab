#!/usr/bin/env python3

# Import PySide classes
import sys, collections, json, tabulate, shutil
import argparse

from pathlib import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import QWebView
from PyQt5.QtWebKit import QWebSettings
from PyQt5.QtNetwork import QNetworkRequest
from PyQt5.QtNetwork import QNetworkRequest
from PyQt5.QtPrintSupport import QPrinter

import urllib.parse

Signal = pyqtSignal
Slot = pyqtSlot

parser = argparse.ArgumentParser(description='Process some integers.')
# parser.add_argument('htmlfile', nargs=1, required=True, type=argparse.FileType('r'), default=sys.stdin)
parser.add_argument('htmlpath', type=Path)
parser.add_argument("-s",'--show', action='store_true')
parser.add_argument("-o",'--output', nargs=1, default="", type=str)

def process_html(htmlpath, args, app):
    
    
    htmlurl = urllib.parse.quote(htmlpath.resolve().absolute().as_posix())
    htmlQurl = QUrl("file://{}".format(htmlurl))
 
    pdfOutputPath = htmlpath.with_suffix(".pdf")
    
    print("htmlpath:", htmlpath)
    print("htmlurl:", htmlurl)
    print("htmlQurl:", htmlQurl)
    print("pdfOutputPath:", pdfOutputPath)
    
    web = QWebView()
    web.page().settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
    
    printer = QPrinter()
    printer.setPageSize(QPrinter.A4)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(str(pdfOutputPath))
 
    def convertIt():
        web.print_(printer)
        print("Pdf generated")
    
    def closeIt():
        QApplication.exit()
 
    web.loadFinished.connect(convertIt)

    if args.show:
        web.show()
    else:
        web.loadFinished.connect(closeIt)
    
    web.load(htmlQurl)
    

class TestWindow(QWidget):
    def __init__(self, web, parent=None):
        super(TestWindow, self).__init__(parent)
        
        self.web = web
        
        mainLayout = QGridLayout()
        mainLayout.addWidget(self.web, 0, 0)
        self.setLayout(mainLayout)
        self.setWindowTitle("Web Preview")


def main():
    args = parser.parse_args()
    
    print("args:",args)
    
    # print("htmlpath", args.htmlpath.absolute())
    
    app = QApplication(sys.argv)

    process_html(args.htmlpath, args, app)
    
    # tw = TestWindow(web)
    # tw.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()