#!/usr/bin/env python3

from pathlib import Path
import sys, collections, logging, traceback, io, multiprocessing, copy, time

from contextlib import contextmanager

@contextmanager
def setupStdLogs(logStdOutFile, logStdErrFile):
    
        out, err = sys.stdout, sys.stderr
        sys.stdout = logStdOutFile 
        sys.stderr = sys.stdout # for now...
    
        yield
    
        sys.stdout, sys.stderr = out, err
        
    
@contextmanager
def setupStdFiles(logStdOutPath, logStdErrPath):
    with open(str(logStdOutPath),'a+') as outfile, open(str(logStdErrPath),'a+') as errfile:
            
        with setupStdLogs(outfile, errfile) as fileLogging:
            print("[Redirecting StdOut]")            
            yield
            print("[Resetting StdOut]")


def guitestprocess(testinfodict, fs, args, logFileNames):
    
    with setupStdFiles(*logFileNames) as logging: # setup for logging output!
    
        from scilab.tools.project import DataTree, debug
        from scilab.tools import testingtools

        import scilab.datahandling.dataprocessor as dataprocessor
        from scilab.expers.configuration import FileStructure, generatetestinfoclass
    
        print("### Processing ")
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
