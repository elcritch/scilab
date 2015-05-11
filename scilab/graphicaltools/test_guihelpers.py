#!/usr/bin/env python3

import forms

from forms import fedit


def test():
    
    datalist = [
        ('Area:', 1.9),
        ('Min Area:', 1.3),
        ('Gauge:', 7.9),
        ]

    dataout = forms.fedit(datalist)
    print(dataout)
    
if __name__ == '__main__':
    test()