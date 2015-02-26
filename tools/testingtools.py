#!/usr/local/bin/python3

import contextlib, io, sys, os
from functools import wraps

class TeeIO:
    def __init__(self, fd1, fd2):
        self.fd1 = fd1
        self.fd2 = fd2

    def write(self, text):
        self.fd1 and self.fd1.write(text)
        self.fd2 and self.fd2.write(text)

    def flush(self):
        self.fd1 and self.fd1.flush()
        self.fd2 and self.fd2.flush()
        
    def close(self):
        pass



def test_in(tests):
    def test_decorator(func):
        @wraps(func)
        def test_wrapper(*args, **kwargs):
            if not getattr(tests, 'quiet', None):
                print("\n### {} ###".format(func.__name__))
            try:
                return func(*args, **kwargs)
            except Exception as err:
                # print("Error:", err)
                raise err
        tests['append'](test_wrapper)
        return test_wrapper
    return test_decorator



@contextlib.contextmanager
def Tests(tests=None, quiet=True, ):
    before = set(globals())
    
    tests = tests if tests else []
    context = dict(append=lambda x: tests.append(x), quiet=quiet, batch=True)
        
    yield context

    after = set(globals().keys())
    
    for testvar in (after - before):
        # print("del:",testvar)
        del globals()[testvar]
    
    def do_tests(quiet):
        out = sys.stdout if not quiet else open(os.devnull, 'w')
        stdout = sys.stdout
        with contextlib.redirect_stdout(out):
            quiet and print("Running {} Test(s): [ ".format(len(tests)), end='', file=stdout)
            for test in tests:
                quiet and print("{}, ".format(test.__name__), end='', file=stdout)                
                test()
                # quiet and print('.', end='', file=stdout)
            # quiet and print('\n', file=stdout)
            quiet and print(" ] ", end='\n\n', file=stdout)
    
    print("## Executing Tests ##")
    do_tests(quiet)
    print("Finished Executing Tests")
    
    del tests
    

def tests():
    with Tests(quiet=False) as tests:

        foobar = []
    
        @test_in(tests)
        def example_test_tests_1():
            """ test debug """
            foobar = [1,2,3]
            foolist = ["a","b"]
            print(foobar, foolist)

        @test_in(tests)
        def example_test_tests_2():
            """ test debug """
            foobar = [1,2,3]
            foolist = ["aaaa","bbbbb"]

    with Tests(quiet=True) as tests:

        foobar = []
    
        @test_in(tests)
        def example_test_tests_1():
            """ test debug """
            foobar = [1,2,3]
            foolist = ["a","b"]

            print(foobar, foolist)    

            print(foobar, foolist)

if __name__ == '__main__':
    tests()