#!/usr/bin/env python3

import sys, os, glob, logging, collections
from collections import namedtuple
from pathlib import Path
import xmltodict 
from collections import OrderedDict

import matplotlib.pyplot as plt
import scilab

from scilab.tools.project import *
import numpy as np
import scilab.tools.fitting as Fitting
import scilab.tools.jsonutils as Json
import scilab.datahandling.datahandlers as datahandlers
import mistune


import seaborn as sns


def filetime(v):
    return time.strftime("%m/%d/%Y %H:%M:%S", time.gmtime(v.stat().st_mtime)) if v.exists() else "" 

def itemHandler(k,v):
    shape, shapeName, shapeFields = shapeof(v)
    if shape == "mapping" and shapeName:
        shapetuple = collections.namedtuple(shapeName, shapeFields)
        return shapetuple(**v)
    elif shape == "mapping":
        return mapd(v, valuef=itemHandler)
    elif shape == "namedtuple":
        if shapeName == "valueIndex": return itemHandler(k, v.value)
        return v
    elif shape == "number":
        nv = v
        return nv
    else:
        return v

def formatHandler(k,v):
    shape, shapeName, shapeFields = shapeof(v)
    
    if shape == "mapping" and not shapeName:
        return mapd(v, valuef=formatHandler)
    elif shape == "namedtuple":
        try:
            try:
                ff = lambda x: float('nan') if x == None else x
                if all( ( not i for i in v ) ): return ""
                if shapeName == "valueIndex": return "{:.2f}".format(*v)
                if shapeName == "valueIndexUnits": return "{0:.2f} <code>{1}</code>".format(ff(v[0]), v[2])
                if shapeName == "valueUnitsStd": return "{0:.2f} ± {2:.2f} <code>{1}</code>".format(ff(v[0]), v[1], ff(v[2]))
                if shapeName == "valueUnits": return "{0:.2f} <code>{1}</code>".format(ff(v[0]), v[1])
                if shapeName == "linearFit": return "{0:.2f}/{1:.2f}".format(ff(v[0]), ff(v[1]))
            except ValueError as err:
                return " ".join([ str(v) for i in v ])
        except Exception as err:
            display(HTML(debugger_summary("formatHandler", locals())))
            raise err
    elif shape == "number":
        return "{:.3f}".format(v)
    else:
        return v

def makeTestDocument(test, args):
    
    fields = test.data.tablefields
    ddetails = test.data.summarydetails
    fdetails = test.data.flatdetails
    graphNames = test.data.graphnames
    
    testdir = test.folder.main
    infoStr = str(test.info)
    
    # make tables
    tables = collections.OrderedDict(
        infosTable=tabulate.tabulate( [test.info], headers=test.info._fields, tablefmt ='pipe' )
    )
    
    _done = set()
    def done(k):
        ret = k in _done
        _done.add(k)
        return ret
    
    for name, tableconfig in fields.items():
        
        if isinstance(tableconfig, OrderedDict):
            data = [ (k, fdetails[v]) for k,v in tableconfig.items() if not done(v) ]
            # summarykeys.add( ('Test',)+ tuple( i[0] for i in data )+('Preload',) )
            # summarydata.append( [ i[1] for i in data ])
            # summarydata[-1].insert(0,test.info.short)
            tab = tabulate.tabulate(data, headers=["Name", "Value"], tablefmt ='pipe' )
        elif isinstance(tableconfig, list):
            values = OrderedDict()
            [ values.update( flatten(ddetails[key], parent_key=key) ) for key in tableconfig ]
            data = [ (" ".join(k.split('.')[:-1]), k.split('.')[-1], v) 
                            for k,v in flatten(values).items() if not done(k) ]
            tab = tabulate.tabulate(data, headers=["Group", "Field", "Value"], tablefmt ='pipe' )
        
        tables[name] = "#### {}\n\n".format(name) + str(tab)
    
    specimenImagesHtml = "\n".join([ 
                    "<img src='{}' width='{}%'></img>".format(img.relative_to(testdir), 28 )
                        for img in test.folder.images.glob("processed/*.cropped.png") 
                    ])
        
    # graphNames = [
    #     ('UTS', "*norm*graph=uts*.png"),
    #     ('Precond Fit', "graph*norm*graph=precond_fit*.png"),
    #     ('Overview Precond', "graph*norm*method=*precond*graph=overview*.png"),
    #     ('Overview Preload', "graph*raw*method=*preload*graph=overview*.png"),
    # ]
    
    debug(graphNames)
    graphFiles = [ (k,next(test.folder.graphs.glob(v), test.folder.graphs/v)) for k,v in graphNames ]
    
    graphsHtml = "\n".join([ 
            "<tr><td><h3>{name}</h3><br><img width='100%' src='{src}'></img><pre>{src}</pre></td></tr>".format(
                src=img.relative_to(testdir), name=n )
                for n, img in graphFiles ])

    specimenMeasurementsHtml = "\n".join([ 
                    "<img src='{}' width='{}%'></img><br>".format(img.relative_to(testdir), 80 )
                        for img in test.folder.graphs.glob("*graph=imagemeasurement*v{version}*".format(version=args.version)) 
                    ])

    #fileTable = tabulate.tabulate( sorted([ 
    #                (k,v.relative_to(testdir) , 
    #                 "&#10003;" if v.exists() else "<em>&#10008;</em>", 
    #                 filetime(v)) 
    #                    for k,v in flatten(test.folder).items() 
    #                ]), [ "Name", "Folder", "Exists", "Modified Time" ], tablefmt ='pipe' )
    
    dataFilesTable = ""
    
    configs = datahandlers.datacombinations(test, args=args, items=["tracking"], )
    dataFilesTable += tabulate.tabulate( 
        [ (
                k, 
                 v.relative_to(testdir).suffix ,
                 "&#10003;" if v.exists() else "<em>&#10008;</em>",
                 filetime(v)
          )
         for k,v in flatten(configs).items() 
        ], 
        headers=[ "Name", "Exists", "Modified Time" ], 
        tablefmt='pipe' )
    
    tables.update(**{ k:v for k,v in locals().items() if 'Table' in k or 'Html' in k or 'Str' in k })
    
    print("\n\nTestTemplate:\n\n")
    debug(test.reportconf["TestTemplate"])
    
    
    testTemplate = test.reportconf["TestTemplate"]
    testTemplate = testTemplate["#text"] if not isinstance(testTemplate, str) else testTemplate
    testTemplate = testTemplate.strip() 
    
    print('\n')
    print(testTemplate)
    
    return testTemplate.format(info=test.info, **tables)


def processTestDocument(test, args):
    
    print("## {} ".format(test.info))
    
    reportStr = makeTestDocument(test, args)
    
    reportFilename = "report (Test Summary ; short={short} ; v{version})"
    reportFilename = reportFilename.format(short=test.info.short, version = "12")
    reportPathname = (test.folder.path / reportFilename).with_suffix(".md")
    reportHtmlPathname = (test.folder.path / reportFilename).with_suffix(".html")
    debug(reportFilename, reportPathname)
    
    with open(str(reportPathname),'w', encoding='utf-8') as report:
        report.write(reportStr)

    if args.options["output", "html", "auto"]:
        reportHtmlStr = mistune.markdown(reportStr)
        
        with open(str(reportHtmlPathname),'w', encoding='utf-8') as report:
            report.write(reportHtmlStr)
        
        
    mdfile = "{file}".format(file=(test.folder.main / reportFilename))

    return mdfile, reportStr

def load_xml(pathurl):
    
    pathurl = Path(str(pathurl))
    
    with pathurl.open('r') as file:
        contents = file.read()
    
    xmldict = xmltodict.parse(contents)
    
    return xmldict
    
def processReportConfig(testconf, args):
    
    reportconf = load_xml(testconf.projectfolder.project / "report.xml")    
    reportconf = reportconf["ReportDefinition"]
    
    testconf.reportconf = reportconf
    
    debug(reportconf)
    
    tablefields = collections.OrderedDict()
    
    for table in reportconf["Table"]:
        name = table["@name"]
        print()
        debug(table)
        
        if "@custom" in table:
            accessors = collections.OrderedDict( (f["@name"], f["@field"]) for f in table["Field"] )
        else:
            debug(table["Fields"])
            accessors = list( f["@field"] for f in [table["Fields"],] )
        
        debug(accessors)
        tablefields[name] = accessors
    
    graphnames = []
    
    for graph in reportconf["GraphTable"]["Graph"]:
        graphname = ( graph["@name"], graph["@match"].format(version=args.version) )
        graphnames.append(graphname)
        
    testconf.data.graphnames = graphnames
    
    # for line in fieldNames.strip().split("\n"):
    #     name, table, accessor = [ s.strip() for s in line.split('|') ]
    #     fields[table][name] = accessor
    #
    # fields['Measurements'] = [ "measurements" ]
    # fields['Excel'] = [ "excel" ]
    # fields['Variables'] = [ "variables" ]
    testconf.data.graphnames = graphnames
    testconf.data.tablefields = tablefields
    
    return tablefields


def generatepdfs(file):

    scilabparent = Path(scilab.__file__).resolve().parent.parent
    mdprocessor = subprocess.check_output("which scholdoc", shell=True).decode('utf8').strip()
    scripthtml = scilabparent / "scripts" / "preview_scholdoc.sh"
    scriptpdf = scilabparent / "scripts" / "run_scholdoc.sh"

    scripthtml.resolve(), scriptpdf.resolve()
    debug(mdprocessor, scriptpdf, scripthtml)

    pandocjob = "{script} '{file}.md' {pd}".format(script=scriptpdf, file=file, pd=mdprocessor )

    try:
        print(pandocjob)
        print(subprocess.check_call (pandocjob, shell=True) )
    except Exception as err:
        raise err


def process_test(testconf, args):
    
    if args.options['output','dataprocessor','skipreports']:
        print("Not running reports.")
        return
        
    origtestdetails = Json.load_json_from(testconf.folder.details)
    
    testdetails = mapd(origtestdetails, valuef=itemHandler)
    testdetails = mapd(testdetails, valuef=formatHandler)

    processReportConfig(testconf, args)
    
    testconf.data.summarydetails = testdetails
    testconf.data.flatdetails = DataTree(flatten(testdetails))
    
    jsonlfilename = "data (type=flat summary ; kind=json ; short={short} ; v{version}).jsonl"
    jsonlfilename = jsonlfilename.format(short=testconf.info.short, version=args.version)
    jsonlfilename = testconf.folder.main / jsonlfilename
    
    # with jsonlFilename.open('w') as jsonlfile:    
    Json.write_json_to(jsonlfilename, flatten(origtestdetails), indent=None)
    
    mdfile, reportStr = processTestDocument(testconf, args)

    
    if args.options["output", "generatepdfs"]:
        generatepdfs(mdfile)
    else:
        print("Not generating pdfs. ")
    
    # print("Job:", subprocess.check_call(job, shell=True), flush=True )
    

def process(test, args):
    
    try:
        process_test(test, args)
    
    except Exception as err:
        
        logging.exception("Report Error: %s error: %s"%(test.info.short,err))
    
        raise err
    
    
    
    