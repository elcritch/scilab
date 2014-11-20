#!/usr/bin/env python3

import json, os, tempfile, shutil, logging

import jsonmerge 

if __name__ != '__main__':
    from ntm.Tools.Project import *
else:
    from Project import *
    

def get_data_name(file_name):
    ## Handle Names    
    name = os.path.basename(file_name)
    if 'csv' in file_name:
        name = name.replace('.steps.tracking.csv', '.csv')
        name = name.replace('.steps.trends.csv', '.csv') # temp holder
    
    name = os.path.splitext(name)[0]
    
    ## Get Test ID 
    match = re.match(r'(.+)\((.+)-(.+)\)[-]*(.+?)-(.+?)-(.+?)-(\w+)(?:-(.+))*', name)
        
    testDate, sample, section, orientation, zone, layer, specimen = match.groups()[:7]
    
    # strip tests
    name = '{}({}-{})-{}-{}-{}-{}'.format(testDate, sample, section, orientation, zone, layer, specimen)
    
    nums = lambda s: ''.join( c for c in s if c.isdigit() )
    
    testId = '.'.join(map(nums,sample.split('.')))+'.'+nums(zone+layer+specimen)
    
    return (name, testId)
    
    
def load_data(parentdir, test_name, dataDir="../../test-data/", dbg=None):
    
    test_name = get_data_name(test_name)[0]
    
    dataDir = os.path.realpath(parentdir+"/"+dataDir)
    print("load_data:",dataDir)
    data = load_json(dataDir, json_url=test_name+".json")
    
    return data

def update_data(parentdir, test_name, data, dataDir="../../test-data/", dbg=None):
    test_name = get_data_name(test_name)[0]
    
    dataDir = os.path.realpath(parentdir+"/"+dataDir)
    print("update_data:",dataDir)
    update_json(dataDir, data, json_url=test_name+".json")
    
    return 

# def load_json(parentdir, json_url="data.json"):
#
#     json_path = os.sep.join( [parentdir, json_url, ] )
#     with open( json_path ) as json_file:
#         json_data = json.load(json_file)
#
#         return json_data
    
def load_json(parentdir, json_url="data.json", datatree=False):
    
    json_path = os.sep.join( [parentdir, json_url, ] )
    
    try:
        with open( json_path ) as json_file:

            dt = DataTree()
            def as_datatree(dct):
                tree = DataTree()
                tree.update(dct)
                return tree

            json_data = json.load(json_file, object_hook=as_datatree)
            # else:
            #     json_data = json.load(json_file)
        
            return json_data
            
    except Exception as err:
            
            try:
                # try print json raw
                with open( json_path ) as json_file:
                    print(''.join(json_file.readlines()))
            except FileNotFoundError as err2:
                logging.warn("Json File not found: "+json_path)
                return None
                
            raise err 
    
def write_json(parentdir,json_data, json_url="data.json", dbg=None):
    json_path = os.sep.join( [parentdir, json_url, ] )
    
    with tempfile.NamedTemporaryFile('w',delete=False) as tempFile:
    
        if dbg:
            debug(json_path)
            print(json.dumps(json_data, indent=4))
    
        # with open( tempFile, 'w' ) as json_file:
        # with tempFile as json_file:
        json.dump(json_data, tempFile, indent=4)

            # update json file
            # debug(tempFile.name)
    
    os.rename(tempFile.name, json_path)
    
    return

    
def update_json(parentdir, update_data, json_url="data.json", dbg=None):
    """ Simple update method. Needs to handle merging better.  """
    
    json_data = load_json(parentdir)
    json_to_write = jsonmerge.merge(json_data, update_data)
    
    write_json(parentdir, json_to_write, dbg=dbg)
    
    return
    
