#!/usr/bin/env python3

import os, sys, pathlib, re, logging, shutil
import pandas as pd
import numpy as np
import scipy.io as sio
from pandas import ExcelWriter

import scilab
import scilab.tools.jsonutils as Json
from scilab.tools.project import *
from scilab.expers.configuration import *
from scilab.tools.instroncsv import *

from scilab.datahandling.datahandlers import *
import scilab.datahandling.columnhandlers as columnhandlers  
import scilab.datahandling.datasheetparser as datasheetparser  
import scilab.datahandling.processimagemeasurement as processimagemeasurement
import scilab.datahandling.processingreports as processingreports
import scilab.utilities.merge_calculated_jsons as merge_calculated_jsons
import scilab.expers.mechanical.fatigue.run_image_measure as run_image_measure

import scilab.datagraphs.graph_runner3_cycles as cycles_graph_runner
import scilab.datagraphs.graph_runner3_uts as uts_graph_runner

import numpy as np

import xmltodict
from tabulate import tabulate

# @debugger
def resolve(url):
    return Path(url).resolve()


def process_raw_columns(data, raw_config, state):

    # === Handle Raw Files === 
    handle_files(data, state.methoditem, state, state.testfolder)
    rawdata = data.file.data
    
    csv_cols_index_full = { v.full.strip(): v for v in data.file.data.values() 
                                    if isinstance(v, InstronColumnData) }
    
    debug(list(csv_cols_index_full.keys()))
    
    output = []
    
    for rawcol in raw_config.columns:
        print("<i>Raw Column:<i> {}".format(repr(rawcol.info)))        
        
        # ============================================================
        # = Handle Raw Columns with multiple possible row conditions =
        # ============================================================
        if rawcol.get('source', None):
            env = DataTree(details=state.details, **data)
            sourcecol = getproperty(rawcol.source, action=True, env=env)
            # fullsourcename = next([ o.full for o in output if o.name == sourcecol])
            # fulls.append(fullsourcename)
            if sourcecol[0].isspace():
                raise ValueError("Column Names cannot include spaces!", sourcecol, rawcol)
            debug(sourcecol, [ (rc.name, oc.name,rc.name==sourcecol, sourcecol) for rc,oc in output ])
            origcol = [ oc for rc,oc in output if rc.name == sourcecol ][0]
            output.append((rawcol.info, origcol))
        else:
            # otherwise process "full" name(s)
            fulls = rawcol.get('fulls',[])
            
            # first add any single names
            if rawcol.info.get('full', None):
                fulls.append(rawcol.info.full)
        
            # next check for 
            for full in fulls:
                rawcol.info.full = full
                if full in csv_cols_index_full:
                    break
        
            if full not in csv_cols_index_full:
                debughere()
                cols = ''.join(map("<li>{}</li>".format, csv_cols_index_full.keys()))
                msg = "Column Missing from Data: column: `{}` data file columns: \n<ul>{}</ul>".format(
                    repr(rawcol.info.full), cols)
                print(msg)
                raise KeyError(msg)        
        
            output.append((rawcol.info, csv_cols_index_full[full]))
    
    return output 

def normalize_columns(data, norm_config, filenames, state):    
    output = []
    
    get_attr_to_item = lambda xs: ''.join([ "['%s']"%x for x in xs.split('.')])
    re_attribs = lambda k, s: re.sub(r"(%s)((?:\.\w+)+)"%k, lambda m: print(m.groups()) or m.groups()[0]+get_attr_to_item(m.groups()[1][1:]), s)
            
    # @debugger
    def _normalize(col):

        env = DataTree(details=state.details, **data)
        sourcecol = getproperty(col.source, action=True, env=env)

        if sourcecol:
            print(mdHeader(4, "Column: {}", sourcecol))
        
            normeddata = executeexpr("raw.data.{col}".format(col=sourcecol), **env)
            normedinfo = executeexpr("raw.columninfo.{col}".format(col=sourcecol), **env)
            normedinfo = DataTree( ((f,getattr(normedinfo,f)) for f in normedinfo._fieldnames) )    
            col.info = normedinfo.set(**col.get('info',{}))
        else:
            normeddata = None
        
        exec_variables = state.get('variables',DataTree())
        props = exec_variables[state.methodname][state.methoditem.name][state.processorname]
        
        if col['conversion','constant']:
            key, constantexpr = getpropertypair(col.conversion)
            constant_factor = executeexpr(constantexpr, details=state.details, data=data, props=props, variables=exec_variables)
            debug(constant_factor)
            normeddata = normeddata * constant_factor
        if col['conversion','func']:
            key, constantexpr = getpropertypair(col.conversion)
            normeddata = executeexpr(constantexpr, x=normeddata, details=state.details, data=data, props=props, variables=exec_variables)
            
        
        return normeddata
    
    # ====================================================
    # = Process Normalized Columns (one column per item) =
    # ====================================================
    for col in norm_config.columns:
        normedcoldata = _normalize(col)
        # debug(normedcoldata)
        print("Normed data name:{} shape:{}".format(col.info.label, normedcoldata.shape))
        print()
        
        normcol = DataTree(array=normedcoldata, summary=summaryvalues(normedcoldata, np.s_[0:-1]))
        output.append( [ col.info, normcol ] )
        data['norm',col.info.name] = normcol.array
    
    return output 

    
def process_variables(testfolder, state, name, kind:"pre|post", data):
    print("### Processing Variables ")
    
    variables_input = state['methoditem','variables', name, kind]
    
    # debug(state)
    
    if not variables_input: 
        variables = DataTree()
    else:
        env = DataTree(projdesc=state.projdesc, details=state.details, codehandlers=state.args.codehandlers, **data )
        variables = getproperty(variables_input, action=True, env=env)

    state.variables = variables

    vardict = DataTree()
    vardict[ tuple( i[1] for i in state.position )+(name, kind, ) ] = variables
    # debug(vardict)
    # print(vardict)
    
    jsonpath, allvariables = testfolder.save_calculated_json(
        test=state.args.testconf, 
        name="variables", 
        data=vardict,
        # mergeschema={"properties": {'m3_cycles': {'tracking': {'norm': {'post': {"mergeStrategy": "overwrite"} }}}, 'tracking': {"mergeStrategy": "overwrite"} } },
        )
    
    state.variables.update( allvariables["variables"] )
    # debug(allvariables, state.variables)
    
    return 
    
    
def process(testfolder, data, processor, state):    
    try:
        configs = { p["name"]: p for p in processor }
        raw_config = configs.get("raw", None)
        normalized_config = configs.get("norm", None)

        
        default_index = [{"column":'step',"type":"int"},]
        save_config = DataTree(projdesc=json.dumps(state.projdesc))
        header=OrderedDict(method=state.methodname, item=state.methoditem.name)
        def missingFiles(x): 
            missing = [ k for k,v in x.items() if not v.exists() ]
            debug(missing)
            return missing
    
        # forceRuns = state.args.get('forceRuns',DataTree())
        forceRuns = state.args.options["dataprocessor", "forcerun"] 
        
        debug(forceRuns)
        
        # varfilename = "{methodname}.{methoditem.name}.calculated".format(**state)
        # testfolder.save_calculated_json(test=state.args.testconf, name="variables", data={}, overwrite=True)
        
        # ====================
        # = Process Raw Data =
        # ====================
        print(mdHeader(3, "Raw Data"))
    
        output = DataTree()
        output['raw','files'] = getfilenames(
            test=state.args.testconf, testfolder=testfolder, stage="raw", 
            version=state.args.options["dataprocessor", "version"], 
            header=header, matlab=True, excel=state.args.options["output","excel",])
    
        rawdata = None
        
        print("Checking Raw files: forceRuns:`{}`, missing output:`{}`".format(
                forceRuns['raw',], missingFiles(output.raw.files.names)))
        
        if raw_config and (forceRuns['raw',] or missingFiles(output.raw.files.names)):
            if not state.args.options["output","onlyVars",]:
                missingFiles(output.raw.files.names)
                columnmapping = process_raw_columns(data, raw_config, state)
                indexes = default_index + raw_config.get('_slicecolumns_', [])
                save_columns(columnmapping=columnmapping, indexes=indexes, configuration=save_config, filenames=output.raw.files)
                
            if state.args.options["output","rawcalcs"]:           
                
                print(mdHeader(4, "Running Raw variables"))
                 
                rawdata = load_columns(output.raw.files.names, "matlab")
            
                ## save variables
                data = DataTree(raw=rawdata)
                # data.raw = DataTree(**columnmapping_vars(columnmapping))
                process_variables(testfolder, state, raw_config.name, "post", data)
                      
            # else:
            #     print("Skipping saving `raw` columns. Only updating variable json. ")
        else:
            print("Skipping processing `raw` stage.")


        # =====================
        # = Process Norm Data =
        # =====================
        print(mdHeader(3, "Normalize Data"))

        output['norm','files'] = getfilenames(
            test=state.args.testconf, testfolder=testfolder, stage="norm", 
            version=state.args.options["dataprocessor", "version"], 
            header=header, matlab=True, excel=state.args.options["output","excel"])
        
        print("Checking Norm files: forceRuns:`{}`, missing output:`{}`".format(
                forceRuns['norm',], missingFiles(output.norm.files.names)))
        
        if normalized_config and (forceRuns['norm',] or missingFiles(output.norm.files.names)):
            
            normstate = state.set(processorname=normalized_config.name)
            
            if not rawdata:
                rawdata = load_columns(output.raw.files.names, "matlab")
            
            data = DataTree(raw=rawdata)
            
            # ======   Save Pre Variables  ====== #
            process_variables(testfolder, normstate, normalized_config.name, "pre", data)

            # ====== Normalize Columns ====== #
            columnmapping = normalize_columns(data, normalized_config, output.norm.files, normstate)
            indexes = [{"column":'step',"type":"int"}] + normalized_config.get('_slicecolumns_', [])
            
            # ======   Save Post Variables  ====== #
            normdata = columnmapping_vars(columnmapping)
            data.norm = DataTree(**columnmapping_vars(columnmapping))
            process_variables(testfolder, state, normalized_config.name, "post", data)
                        
            if not state.args['onlyVars',]:
                save_columns(columnmapping=columnmapping, indexes=indexes, configuration=save_config, filenames=output.norm.files)
            else:
                print("Skipping saving `norm` columns. Only updating variable json. ")
        else:
            print("Skipping processing `norm` stage. ")
            
            
            
    except Exception as err:
        # debughere()
        raise err



def handle_files(data, methoditem, state, testfolder):
    
    if 'files' in methoditem:
        
        print("### Handle Raw Files")
        env = DataTree(details=state.details, testfolder=testfolder, projectfolder=state.filestructure)
        # import json
        # print(json.dumps(env, cls=CustomDebugJsonEncoder))

        try:
            filetype, filevalue = getpropertypair(methoditem.files)
            debug(filevalue)
            
            filename = safefmt(getproperty(filevalue, action=True, errorcheck=False, env=env),**env)
            debug(filename)
            filepath = matchfilename(filename, strictmatch=False)
            debug(filepath)
        except Exception as err:
            # logging.error("Error looking up file: ", err)
            raise Exception("Cannot find file for ", err, ['optional'])
            # raise ProcessorException("Cannot find file for pattern: {} in method: {}".format(filevalue, methoditem.name), err)
        
        if filepath and filepath.exists():
            data.file = getproperty(DataTree(_csv_=filepath), action=True, env=env)
        else:
            # print(debugger_summary("handle_files", state, ignores=['filestructure.projdesc','args', 'details']))
            # print(debugger_summary("handle_files:locals", locals(), ignores=['builtins', 'state', 'data', 'methoditem'] ))
            # if filenameerr:
            #     raise Exception("format exception:",filevalue, filenameerr)
            
            # raise ProcessorException("Cannot find file for pattern: {} in method: {}".format(filevalue, methoditem.name), err )
            raise ProcessorException("Cannot find file for pattern: {} in method: {}".format(filevalue, methoditem.name),['optional'])



def process_method(methodname, method, testfolder, projdesc, state):
        
    files = DataTree()
    
    for methoditem in method:
        
        print(mdHeader(3, "Method Item: {} ".format(methoditem.name)))
        # ================================================
        debug(methoditem)
        
        
        testdetails = Json.load_json_from(testfolder.details)
        state.details = testdetails
        state.methoditem = methoditem
        # = Files =
        data = DataTree()
            
        # ====================
        # = Handle Processor =
        # ====================
        processorname = methoditem.processor['$ref'].lstrip('#/processors/')
        print(mdHeader(4, "Processor: {}".format(processorname)))
        processor = projdesc.processors[processorname]

        itemstate = state.set(methoditem=methoditem, methodname=methodname)
        push(itemstate, 'methoditem',methoditem.name)        
        debug(itemstate.position)
        itemstate.testfolder = testfolder
        process(testfolder=testfolder, data=data, processor=processor, state=itemstate)


def process_methods(testfolder, state, args):

    # debug(state.filestructure.projdesc)
    
    projdesc = state.filestructure.projdesc
    state.projdesc = projdesc
    
    for methodprop in projdesc.methods:
        try:
            methodname, method = getpropertypair(methodprop)
        
            print(mdHeader(2, "Data Method: `{}` ".format(methodname)))
            substate = state.set(methodname=methodname, method=method)
            push(substate, 'methodname',methodname)
            process_method(methodname, method, testfolder, projdesc, state=substate)
        except Exception as err:
            print("type:",str(type(err.args[-1])).replace('<','≤'))
            if args.options["dataprocessor", "optional_errors"] and \
                    isinstance(err.args[-1],(tuple,list)) and 'optional' in err.args[-1]:
                logging.warning(str(err))
                continue
            else:
                raise err
        
def run(filestructure, testfolder, args):
    
    # ==================
    # = Set Arguements =
    # ==================
    
    state = DataTree()
    state.args = args
    state.filestructure = filestructure
    state.position = []
    
    # push(state, 'testinfo', args.testconf.info.short)
    # push(state,  'testfolder', testfolder)
    


print("Run normalize_instron_data")



# ====================
# = Script Execution =
# ====================

def display(*args, **kwargs):
    print(*args, **kwargs)

def HTML(arg, whitespace=None):
    if whitespace:
        return "<div style='white-space: {whitespace};'>\n{ret}\n</div>\n".format(whitespace=whitespace, ret=arg)
    else:
        ret = arg.replace('\n','\r')
        return ret

def execute(fs, name, testconf, args):
    
    print("\n")
    display(HTML("<h2>Processing Test: {} | {}</h2>".format(testconf.info.short, name)))
    
    folder = fs.testfolder(testinfo=testconf.info)
    
    try:
        processed_link = fs.processed / testconf.info.short 
        if not processed_link.exists():
            debug("../"+str(folder.testdir.relative_to(fs.project)), str(processed_link))
            os.symlink("../"+str(folder.testdir.relative_to(fs.project)), str(processed_link), target_is_directory=True )
    except Exception as err:
        logging.warn("Unable to link processed dir: "+str(err))
    
    #data = [ (k,v.relative_to(fs.project), "&#10003;" if v.exists() else "<em>&#10008;</em>" ) 
    #            for k,v in flatten(folder).items() if v ]
    #data = sorted(data)

    #print()
    #print(HTML(tabulate( data, [ "Name", "Folder", "Exists" ], tablefmt ='pipe' ), whitespace="pre-wrap"))
    #debug(folder.data.relative_to(fs.project))
    
    args.testname = name
    args.testconf = testconf
    args.report = sys.stdout
    
    testconf.folder = folder
    testconf.projectfolder = fs
    
    # Setup Arguments Environment
    state = DataTree()
    state.args = args
    state.filestructure = fs
    state.position = []
    
    debug(args.options)
    
    # update json details
    if args.options["dataprocessor", "exec", "imageMeasurement"]:
        print(mdHeader(2, "Run Image Measurement"))
    
        imageconfstate = state.set(image_measurement=fs.projdesc["experiment_config","config","calibration","image_measurement"])
        processimagemeasurement.process_test(testconf, state=imageconfstate, args=args)
        # run_image_measure.process_test(testconf.info, testconf.folder)
    
    if args.options["dataprocessor", "exec", "datasheetparser"]:
        print(mdHeader(2, "Make JSON Data"))
    
        datasheetparser.handler(testconf=testconf, excelfile=folder.datasheet, args=args)
        merge_calculated_jsons.handler(testinfo=testconf.info, testfolder=testconf.folder, args=args, savePrevious=False)
    
    if args.options["dataprocessor", "exec", "processMethods"]:
    
        print(mdHeader(2, "Executing"))
    
        process_methods(folder, state, args)

    
    if args.options["dataprocessor", "exec", "mergeJsonCalcPost"]:
        print(mdHeader(2, "Merging JSON Data"))
        merge_calculated_jsons.handler(testinfo=testconf.info, testfolder=testconf.folder, args=args, savePrevious=False)

    if args.options["dataprocessor", "exec", "graphs"]:
        print(mdHeader(2, "Running Graphs"))
        expertype = fs.projdesc["experiment_config"]["type"]
        if expertype == "cycles":
            print(mdHeader(3, "Cycles Graphs"))
            cycles_graph_runner.run(test=testconf, args=args)
        else:
            print(mdHeader(3, "UTS Graphs"))
            uts_graph_runner.run(test=testconf, args=args)

    if args.options["dataprocessor", "exec", "generateReports"]:
        print(mdHeader(2, "Generating Report and summary data"))
        processingreports.process_test(testconf=testconf, args=args)


def test_folder(args):
    
    import scilab.expers.configuration as config
    
    
    pdp = args.parentdir / 'projdesc.json' 
    print(pdp)
    # print(pdp.resolve())
    
    fs = config.FileStructure(projdescpath=pdp, verify=True, project=args.parentdir)
    
    # Import Test Specific processors. This needs to be improved!
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
    
    
    # Test test images for now
    test_dir = fs.tests.resolve()
    testitemsd = fs.testitemsd()

    testitems = { k.name: DataTree(info=k, folder=v, data=DataTree() ) for k,v in testitemsd.items()}
    
    summaries = OrderedDict()
    
    for name, testconf in sorted( testitems.items() )[:]:
        # if name != "jan13(gf10.2-rlm)-wa-tr-l6-x3":
        # if 'tr' not in name or name < "nov24(gf9.2-llm)-wa-tr-l5-x2":
        # if name < "jan14":
            # continue
        # if name not in ["jan10(gf10.9-llm)-wa-lg-l10-x2"]:
            # continue
        
        try:
            execute(fs, name, testconf, args, )
            summaries[name] = "Success", "", ""
            
        except Exception as err:
            logging.error(err)
            summaries[name] = "Failed", str(err), "<a src='file://{}'>Folder</a>".format(testconf.folder.testdir.as_posix())
            raise err
    
    print("Summaries:\n\n")
    print(HTML(tabulate( [ (k,)+v for k,v in summaries.items()], [ "Test Name", "Status", "Error", "Folder" ], tablefmt ='pipe' ), whitespace="pre-wrap"))
    print()

def main():
    # test_run()
    args = DataTree()

    # === Excel === 
    args.options = DataTree()
    args.options["dataprocessor", "forcerun", "raw"] = True
    args.options["dataprocessor", "forcerun", "excel"] = False
    args.options["dataprocessor", "version"] = "0"
    args.options["dataprocessor", "optional_errors"]
    args.options["graphicsrunner", "version"] = "0"
    args.options["dataprocessor", "suppress_optional_errors"] = False        
    args.options["output", "excel"] = False
    args.options["output", "onlyVars"] = True
    args.options["output", "generatepdfs"] = False
    args.options["output", "html", "auto"] = True
    args.options["output","rawcalcs"] = True
    
    args.options["dataprocessor", "exec", "imageMeasurement"]  = False
    args.options["dataprocessor", "exec", "datasheetparser"]   = False
    args.options["dataprocessor", "exec", "processMethods"]    = True
    args.options["dataprocessor", "exec", "mergeJsonCalcPost"] = True
    args.options["dataprocessor", "exec", "generateReports"]   = True
    args.options["dataprocessor", "exec", "graphs"]            = False
    
    # parentdir = Path(os.path.expanduser("~/proj/expers/")) / "fatigue-failure|uts|expr1"
    # parentdir = Path(os.path.expanduser("~/proj/expers/")) / "exper|fatigue-failure|cycles|trial1"
    # args.parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper|fatigue-failure|cycles|trial1"
    # args.parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper|fatigue-failure|uts|trial1"
    # args.parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper|fatigue-failure|uts|trial3"
    args.parentdir = Path(os.path.expanduser("~/proj/phd-research/")) / "exper;fatigue-failure;cycles;trial2/01_Raw/tri-modal calibration tests"

    # === Only Update Variables === 
    # print("<a src='file:///Users/elcritch/proj/phd-research/exper|fatigue-failure|cycles|trial1/02_Tests/jan10(gf10.9-llm)-wa-lg-l10-x3/'>Test1</a>")
    # print("<a src='file:///Users/elcritch/proj/phd-research/exper%7Cfatigue-failure%7Ccycles%7Ctrial1/02_Tests/jan10%28gf10.9-llm%29-wa-lg-l10-x3/'>Test1</a>")

    test_folder(args)
    
if __name__ == '__main__':
    main()


