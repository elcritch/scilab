#!/opt/local/bin/python3.3

import shutil, re, sys, os, itertools, argparse, json, glob, collections, functools
import subprocess, urllib


# import openpyxl
# from openpyxl import load_workbook
import os.path as path

import ntm.Tools.ScriptRunner as ScriptRunner
from ntm.Tools.ScriptRunner import RESEARCH, RAWDATA, debug

import logging

from ntm.Tools.Excel import *
from ntm.Tools.Tables import ImageTable, mdHeader, mdBlock, MarkdownTable
from ntm.Tools.Project import *

import ntm.Tools.Json as Json

from itertools import islice, zip_longest

def table_setup(args, **kwargs):
    
    args.state.jsonColumns = jsonColumns = collections.OrderedDict([
        ('set', 'info.set'), 
        ('sample','info.sample'),
        ('gauge','gauge.length'),
        ('area','measurements.area.value'),
        ('E_dyn Amp','dyn_modulus.amp'),
        ('E_dyn Phase','dyn_modulus.phase'),
        ])

    if args.summary_has_uts:
        jsonColumns.update( [
            ('max displacement','calculations.maxes.displacement.value'),
            ('max load','calculations.maxes.load.value'),
            ('maxes strain','calculations.maxes.strain.value'),
            ('max stress','calculations.maxes.stress.value'),
            ])
        
    if args.summary_time_to_load:
        jsonColumns.update([('time to load', 'calculations.time-to-first-loading.time_value')])
    
        
    args.state.summaryTable = MarkdownTable(headers=jsonColumns.keys())
    
    args.state.testDetails = collections.OrderedDict()
    args.state.testImages = collections.OrderedDict()
    
    return


def handler(file_name, file_object, file_path, file_parent, args):
    testFolder = path.basename(file_parent)
    data_json = Json.load_data(file_parent, file_name)

    ## Details 
    
    ### lookup details
    detailValues = [ part.strip() if type(part) is str else part
                        for column in args.state.jsonColumns.values() 
                        for part in [attributesAccessor(data_json, column)] ]

    testName = "%s - %s (%s)"%(detailValues[0], detailValues[1], testFolder)
    
    # debug(detailValues)
    
    ### details table
    detailsTable = MarkdownTable(headers=['Detail', 'Value'])
    detailsTable.add_rows(zip(args.state.jsonColumns.keys(), detailValues))        

    details = detailsTable.generateTable(headers=['Name', 'Value']).format()
    args.state.testDetails[testName] = details
    
    ## Overview Images
    
    ### test overview images 
    testOverviewImages = ImageTable().addImageGlob(file_parent, 'img', '*.png')\
        .addImageGlob(file_parent, "img","overview","*Stress*last*.png")\
        .addImageGlob(file_parent, "img","overview","*Stress*all*.png")\
        .addImageGlob(file_parent, "img","trends","*Stress*all*.png")\
        .addImageGlob(file_parent, "img","trends","*Stress*last*.png")

    ### add details and images to test section
    args.state.testImages[testName] = testOverviewImages
    
    # args.state.tests[testFolder] = [details, images]
    
    ### summary details
    # debug(detailValues)
    args.state.summaryTable.add_row(detailValues)
    
    ## all test images
    allImagesTable = ImageTable().addImageGlob(file_parent, 'img', '**/*.png')
    allImages = allImagesTable.generateTable(columns=2, directory=file_parent).format()
    
    testDetails = [ mdHeader(2, 'Test: '+testName), mdBlock(details), 
                    mdHeader(2, 'All Images'), allImages ]
                    
    writeImageTable(file_parent, 'Test Images ({}).md'.format(testName), testDetails)    
    
    # print 
    print("## CSV Data")
    print('>',','.join(map(str,detailValues)))
        
    return


def writeImageTable(directory, fileName, sections):
    filePath = os.path.join(directory, fileName)
    print("**Writing**:", '`{}`'.format(fileName))
    print('"{}"'.format(os.path.abspath(filePath)))
    print()
    
    with open(filePath, 'w') as file:
        for section in sections:
            # print(mdHeader(2, header), file=file)
            print(section, file=file)
            print('.'*3, end='')
        
        print("\n", file=file)
        print(' done! ')
        
    
def output_table(args):
    
    # if True: return 
    
    project = os.path.join(RAWDATA, args.project)
    
    print('\n\n## Summary Table \n\n')
    print(args.state.summaryTable.generateTable().format())

    ## Make summary markdown 
    summaryFile = "test_summary_table.md"

    summarySections = [ mdHeader(1, "Summary Table"), args.state.summaryTable.generateTable()]

    writeImageTable(project, summaryFile, summarySections)

    ## Make images markdown 
    # imagesMarkdown = os.sep.join(RAWDATA,args.project,"test_all_images.md")
    # writeImageTable(args, imagesMarkdown)
    
    testDetails, testImages = args.state.testDetails, args.state.testImages
    
    def makeTestSection(test, details, images):
        section = ""
        section += mdHeader(3, "Test: "+test)
        section += mdBlock(details)
        section += mdBlock(images.generateTable(columns=2, directory=project))
        return section
        
    testSections = ( makeTestSection(test, details, images) 
                     for (test, details), (_, images) in zip(testDetails.items(), testImages.items()) )
    
    writeImageTable(project, summaryFile, testSections)
        
    print(subprocess.call( ['open', '-a', 'Marked', os.path.join(project, summaryFile)] ))
    # print(subprocess.call( 'open -a Marked 1'.split() + [imagesMarkdown] ))


if __name__ == '__main__':

    parser = ScriptRunner.parser
    parser.add_argument("-n", "--name", default="data", type=str)
    parser.add_argument("--summary-has-uts", action='store_true', default=False, help="Run uts ", )  
    parser.add_argument("--summary-time-to-load", action='store_true', default=True, help="Run time-to-load ", )  

    ## Test
    test_args = []

    ## UTS
    # project = "Test4 - transverse fatigue (ntm-mf-pre)/test4(trans-uts)"
    # test_args += [ "--has-uts", ]

    ## Fatigue
    project = "Test4 - transverse fatigue (ntm-mf-pre)/trans-fatigue-trial1/"
    
    # fileglob = "{R}/{P}/*/*.tracking.csv".format(R="/Users/elcritch/GDrive/Research/",P=project)
    fileglob = "{R}/{P}/*/*.xlsx".format(R=RAWDATA,P=project)
    
    test_args += ["--glob", fileglob] 
    # test_args += ['-1'] # only first
    
    args = parser.parse_args( test_args )    
    args.project = project
    
    # args = parser.parse_args()
    
    if 'args' not in locals():
        args = parser.parse_args()
        
    ScriptRunner.process_files_with(args=args, handler=handler, setup=table_setup, post=output_table)
    
    

    
    
