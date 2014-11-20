#!/opt/local/bin/python3.3

import argparse, re, os, glob, sys
import inspect
import logging

if __name__ != '__main__':
    from ntm.Tools.Project import *
else:
    from Project import *

class GlobAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        print('Debug: %r %r %r' % (namespace, values, option_string))
        
        files = [] 
        dirs = []
        for filename in glob.glob(values):
            if os.path.isfile(filename):
                fileobj = open(filename,'r')
                files.append(fileobj)
            elif os.path.isdir(filename):
                dirs.append( filename )
                
        if not files:
            logging.warning("Did not find any matching files")
            
        setattr(namespace, self.dest, files)
        setattr(namespace, self.dest+'_str', values)
        setattr(namespace, self.dest+'_dirs', dirs)
        

def addDefaultParserArguments(parser):
    parser.add_argument("-g", "--glob", "--glob", type=str, action=GlobAction, default=[],
                        help="Glob: */data/*.xlsx to find all Excel files in the data folder in every folder in the current dir.", )
    parser.add_argument("-f", "--files", nargs='+', type=argparse.FileType('r'), default=[],
                        help="Manual list of files to process", )
    parser.add_argument("-1", "--only-first", action='store_true',  
                        help="Run only the first file from a match or type. ", )
    parser.add_argument("-v", "--verbose", type=int, default=1,
                        help="Verbosity level. ", )

## Default Arguments
parser = argparse.ArgumentParser()
addDefaultParserArguments(parser)
args = None


# process_files_with

def process_files_with(*, args, handler, setup=None, post=None):
    """ Process files defined on the command line. Handler should be a function accepting a fileName, file, and args. """

    args.state = DataTree()
    
    if args.verbose > 0:
        print("\n# Processing ")
    if args.verbose > 1:
        print("> Args: ", args)

    files = args.files 
    glob = args.glob 
    
    all_files = files+glob
    
    if all_files and args.only_first:
        if args.verbose > 0:
            print("Note: Only first file.")
        all_files = all_files[:1]
    
    ## process setup handler
    if setup:
        setup(args)
    
    errors = {}
    
    for file in all_files:
        try:
            ## Handle Files!!
            file_path = os.path.abspath(file.name)
            file_parent, file_name = os.path.split(file_path)
                        
            if args.verbose > 0:
                print("\n## Processing File:", file_name, 'in', " \"%s\" "%file_parent.replace(RESEARCH, '$RESEARCH') , "\n")
            if args.verbose > 1:
                print("> File Object:", str(file), "\n")
                
            handler(file_name=file_name, file_object=file, args=args, file_path=file_path, file_parent=file_parent)
                        
        except Exception as err:
            # logging.exception(err)
            errors[file] = err
            raise err
        
    if post and not errors:
        post(args)
    
    return 
    
def parse_args():
    assert(sys.version_info[0] == 3)
    args = parser.parse_args()
    
    return args



if __name__ == '__main__':

    import tempfile
    
    def testFiles():
    
        p1 = argparse.ArgumentParser()
    
        p1.add_argument('--files', nargs='+', type=argparse.FileType('r'))
        p1.add_argument('--bar', nargs='*')
        p1.add_argument('baz', nargs='*')
        args = p1.parse_args('a b --files /tmp/1 /tmp/2 --bar 1 2'.split())

        for f in args.files:
            print("f:", f.readline())
            
        debug(args)
    
    def testFiles1():
        """ Test file and glob options. Warning this creates temp files! """
        print("\ntestFiles1\n"+'='*80)    
        tempdir = tempfile.mkdtemp()
        debug(tempdir)
        testFiles = []
        for n in range(6):
            name = os.sep.join((tempdir,'TempFile%d'%n))
            with open(name, 'w') as file:
                file.write(name)
                testFiles.append(name)
        
        p1 = parser 

        testArgs = ""
        testArgs += ' --glob %s/TempFile[4-5]'%tempdir
        testArgs += ' --files {}'.format(' '.join(testFiles[:4]))
        args = p1.parse_args(testArgs.split())

        debug(args.files)
        print()
        for f in args.files:
            print("f:", f.readline())
        print()
        for f in args.glob:
            print("fg:", f.readline())
            
        # debug(args)
    
    def testProcessor():
        """ Test file and glob options. Warning this creates temp files! """
        print("\n testProcessor\n"+'='*80)    
        
        tempdir = tempfile.mkdtemp()
        debug(tempdir)
        testFiles = []
        for n in range(6):
            name = os.sep.join((tempdir,'TempFile%d'%n))
            with open(name, 'w') as file:
                file.write(name)
                testFiles.append(name)
        
        p1 = parser 

        testArgs = ""
        testArgs += ' -v1 --glob %s/TempFile*'%tempdir
        args = p1.parse_args(testArgs.split())

        def handler(file_name, **kwargs):
            
            print("File:",file_name)
            print()
            
        process_files_with(args=args, handler=handler)
            
        # debug(args)
    
    def testDebug():
        print("\ntestDebug\n"+'='*80)
        foobar = [1,2,3]
        foolist = ["a","b"]
    
        debug(foobar, foolist)

    ## Run Tests
    
    # testFiles1()
    # testDebug()
    testProcessor()
    