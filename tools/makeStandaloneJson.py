#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

import argparse, json, os, sys

def recStandalone(data, varData):
    """Recursion part for makeStandaloneJson.
    varData is the variables data."""

    if (type(data) is str or type(data) is unicode) and len(data) > 0:
        if data[0] == '@':
            # It's a variable, we replace it with the JSON data
            # It will return an error if the variable doesn't exist, it's intended
            return recStandalone(varData[data[1:]], varData)
        elif '$' in data:
            if '$BUILD_PATH' in data:
                return recStandalone(data.replace('$BUILD_PATH', varData['BUILD_PATH']), varData)
            elif '$ROOT_PATH' in data:
                return recStandalone(data.replace('$ROOT_PATH', varData['ROOT_PATH']), varData)
            elif '$TASK_PATH' in data:
                return recStandalone(data.replace('$TASK_PATH', varData['TASK_PATH']), varData)
        else:
            return data
    elif type(data) is dict:
        # It's a dict, we process the values in it
        newdata = {}
        for k in data.keys():
            newdata[k] = recStandalone(data[k], varData)
        # Is it a fileDescr?
        if newdata.has_key('name') and newdata.has_key('path'):
            newdata['content'] = open(newdata.pop('path'), 'rb').read().decode('utf-8')
        return newdata
    elif type(data) is list:
        # It's a list, we filter the values in it
        newdata = map(lambda x: recStandalone(x, varData), data)
        # We remove None values, which are probably undefined variables
        while None in newdata:
            newdata.remove(None)
        return newdata
    else:
        return data
    

def makeStandaloneJson(data):
    """Makes a 'standalone' JSON file, bundling files referenced by path into
    the JSON to remove any reference to paths."""

    # We try to read a few variables from the JSON data
    varData = {}
    try:
        varData = {'ROOT_PATH': data.get('rootPath', './'),
                   'TASK_PATH': data.get('taskPath', './')}
        try:
            varData.update(json.load(open(os.path.join(data['taskPath'].replace('$ROOT_PATH', data['rootPath']), 'defaultParams.json'), 'r')))
        except:
            pass

        if data.has_key('extraParams'):
            if type(data['extraParams']) is str:
                varData.update(json.load(open(data['extraParams'], 'r')))
            else:
                varData.update(data['extraParams'])
    except:
        pass

    # Start the recursive processing
    return recStandalone(data, varData)


if __name__ == '__main__':
    # Read command line options
    argParser = argparse.ArgumentParser(description="Makes a 'standalone' JSON file, bundling files referenced by path into the JSON to remove any reference to paths.")
    argParser.add_argument('files', metavar='FILE', nargs='*', help='JSON file to transform. If no file is specified, uses stdin as input file, outputs to stdout.')
    args = argParser.parse_args()

    # By default, we make the paths given on command-line absolute
    if len(args.files) > 0:
        for f in args.files:
            print 'Making standalone version of file `%s`...' % f
            try:
                data = json.load(open(f, 'r'))
            except:
                raise Exception("File `%s` does not contain valid JSON data." % f)
            newdata = makeStandaloneJson(data)
            json.dump(newdata, open(f, 'w'))
            
    else:
        try:
            data = json.load(sys.stdin)
        except:
            raise Exception("No valid JSON data received on standard input.")
        json.dump(makeStandaloneJson(data), sys.stdout)
