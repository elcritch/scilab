#!/usr/bin/env python3 

import shutil, re, sys, os, itertools, argparse, json, glob, collections, functools
import subprocess, urllib


# import openpyxl
# from openpyxl import load_workbook
import os.path as path

import scilab.tools.scriptrunner as ScriptRunner
from scilab.tools.scriptrunner import RESEARCH, RAWDATA, debug

import logging

from scilab.tools.excel import *
from scilab.tools.tables import ImageTable, mdHeader, mdBlock, MarkdownTable
from scilab.tools.project import *

import scilab.tools.json as Json
from scilab.expers.mechanical.fatigue.uts import UtsTestInfo
from scilab.tools.tables import mdBlock, mdHeader, ImageTable, MarkdownTable

from itertools import islice, zip_longest


def table_setup(args, **kwargs):
    
    args.state.jsonColumns = jsonColumns = collections.OrderedDict([
        # ('set', 'info.set'), 
        # ('sample','info.sample'),
        ('gauge','gauge.value'),
        ('area','measurements.area.value'),
        ('Linear Modulus','linear_modulus.value'),
        ('Slope Strain','linear_modulus.slope_strain'),
        ('Slope Stress','linear_modulus.slope_stress'),
        ])

    if args.summary_has_uts:
        jsonColumns.update( [
            ('max displacement','calculations.maxes.displacement.value'),
            ('max load','calculations.maxes.load.value'),
            ('maxes strain','calculations.maxes.strain.value'),
            ('max stress','calculations.maxes.stress.value'),
            ])
        
    # if args.summary_time_to_load:
    #     jsonColumns.update([('time to load', 'calculations.time-to-first-loading.time_value')])
    
        
    args.state.summaryTable = MarkdownTable(tablefmt='pipe', floatfmt="0.2", headers=['Id', 'Name', 'Orientation']+list(jsonColumns.keys()))
    
    args.state.testDetails = collections.OrderedDict()
    args.state.testImages = collections.OrderedDict()
    
    return


def handler(test:Path, args:dict):
    
    data_json = Json.load_data_path(test)

    ## Details 
    
    ### lookup details
    detailValues = [ part.strip() if type(part) is str else part
                        for column in args.state.jsonColumns.values() 
                        for part in [attributesAccessor(data_json, column)] ]

    testName = "Test {}".format(test.stems())
    
    if 'n/a' in detailValues:
        debug(detailValues)
        logging.error("Skipping:"+testName+" due to missing details: "+repr(detailValues))
        return
    
    
    
    ### details table
    detailsTable = MarkdownTable(headers=['Detail', 'Value'])
    detailsTable.add_rows(zip(args.state.jsonColumns.keys(), detailValues))        

    details = detailsTable.generateTable(headers=['Name', 'Value']).format()
    args.state.testDetails[testName] = details
    
    ## Overview Images
    
    ### test overview images 
    testOverviewImages = ImageTable()\
        .addImageGlob(str(test.parent), 'img', '*.png')\
        .addImageGlob(str(test.parent), "img","overview","*Stress*last*.png")\
        .addImageGlob(str(test.parent), "img","overview","*Stress*all*.png")\
        .addImageGlob(str(test.parent), "img","trends","*Stress*all*.png")\
        .addImageGlob(str(test.parent), "img","trends","*Stress*last*.png")

    ### add details and images to test section
    args.state.testImages[testName] = testOverviewImages
    
    # args.state.tests[testFolder] = [details, images]
    
    ### summary details
    # debug(detailValues)
    attribs, testId = parse_test_name(test.parent.stems())
    args.state.summaryTable.add_row([testId, test.parent.stems(), attribs.orientation]+detailValues)
    
    ## all test images
    allImagesTable = ImageTable().addImageGlob(str(test.parent), 'img', '**/*.png')
    allImages = allImagesTable.generateTable(columns=2, directory=str(test.parent)).format()
    
    testDetails = [ mdHeader(2, 'Test: '+testName), mdBlock(details), 
                    mdHeader(2, 'All Images'), allImages ]
                    
    writeImageTable(test.parent, 'Test Images ({}).md'.format(testName), testDetails)
    
    # print 
    print("## CSV Data")
    print('>',','.join(map(str,detailValues)))
        
    return


def writeImageTable(directory, fileName, sections, writemode='w'):
    filePath = directory / fileName
    
    debug(filePath)
    
    print("**Writing**:", '`{}`'.format(fileName))
    print('"{}"'.format(filePath))
    print()
    
    with filePath.open(mode=writemode) as file:
        for section in sections:
            # print(mdHeader(2, header), file=file)
            print("section:",section.split('\n')[:3])
            print(section, file=file)
            print('.'*3, end='')
        
        print("\n", file=file)
        print(' done! ')
        
    
def output_table(args):
    
    # if True: return 
    
    project = Path(RAWDATA) / args.project
    
    print('\n\n## Summary Table \n\n')
    summary_table = args.state.summaryTable.generateTable().format()
    print(summary_table)

    ## Make summary markdown 
    summaryFile = "test_summary_table.md"
    summarySections = ( 
        mdHeader(1, "Meniscus Fatigue Expr 1 - Pretrial"), 
        mdBlock('\n\n\n'), 
        mdHeader(2, "Summary Table"), 
        mdBlock(summary_table),
        mdBlock('\n\nDone...\n\n'),
         )

    # writeImageTable(project, summaryFile, summarySections, writemode='w')

    ## Make images markdown 
    # imagesMarkdown = os.sep.join(RAWDATA,args.project,"test_all_images.md")
    # writeImageTable(args, imagesMarkdown)
    
    testDetails, testImages = args.state.testDetails, args.state.testImages
    
    def makeTestSection(test, details, images):
        section = ""
        section += mdHeader(3, "Test: "+test)
        section += mdBlock(details)
        section += mdBlock(images.generateTable(columns=2, directory=str(project)))
        return section
        
    testSections = ( makeTestSection(test, details, images) 
                     for (test, details), (_, images) in zip(testDetails.items(), testImages.items()) )
    
    import itertools
    
    writeImageTable(project, summaryFile, itertools.chain(summarySections, testSections), writemode='w')
        
    print(subprocess.call( ['open', '-a', 'Marked', str(project/summaryFile)] ))
    # print(subprocess.call( 'open -a Marked 1'.split() + [imagesMarkdown] ))


if __name__ == '__main__':

    parser = ScriptRunner.parser 
    parser.add_argument("-n", "--name", default="data", type=str)
    parser.add_argument("--summary-has-uts", action='store_true', default=False, help="Run uts ", )  
    parser.add_argument("--summary-time-to-load", action='store_true', default=True, help="Run time-to-load ", )  

    ## Test
    test_args = []

    ## UTS
    # project = "Test4 - transverse fatigue (scilab.mf.pre)/test4(trans-uts)"

    ## Fatigue
    projectname = 'NTM-MF/fatigue-failure-expr1/'
    projectpath = Path(RAWDATA) / projectname

    files = []
    # files += projectpath.glob('test-data/uts/nov*.json')
    files += projectpath.glob('02*/nov*/*.tracking.csv')

    test_args = []    
    # test_args += ["--glob", fileglob]
    # test_args += ['-1'] # only first
    test_args += [ "--summary-has-uts", ]
    
    args = parser.parse_args( test_args )    
    args.project = projectname
    
    # args = parser.parse_args()
    
    if 'args' not in locals():
        args = parser.parse_args()
        
    # ScriptRunner.process_files_with(args=args, handler=handler, setup=table_setup, post=output_table)
    
    args.state = DebugData()
    table_setup(args)
    
    for test in list(files)[:]:
        
        debug(test)
        
        handler(test=test, args=args)
    
    output_table(args)

    
    
