#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This companion tool to the taskgrader makes a default evaluation JSON for the
# program(s) in FILE(s), using default parameters set in config.py.


import argparse, json, os, sys
from config import CFG_EXECPARAMS, CFG_LANGEXTS

# XXX TODO :: this is a duplicate from taskgrader.py's preprocessJson. Remove
# duplicate after reorganizing code.
def preprocessJson(json, varData):
    """Preprocess some JSON data, replacing variables with their values.
    There's no checking of the type of values in the variables; the resulting
    JSON is supposed to be checked against a JSON schema.
    varData represents the variable data; all values written as '@varname' in
    the JSON will be replaced by varData['varname']."""
    if (type(json) is str or type(json) is unicode) and len(json) > 0:
        if json[0] == '%':
            # It's a variable, we replace it with the JSON data
            # It will return an error if the variable doesn't exist, it's intended
            varName = json[1:]
            if varData.has_key(varName):
                return preprocessJson(varData[varName], varData)
            else:
                # XXX this is changed from taskgrader.py's preprocessJson
                print json
                return json
        else:
            return json
    elif type(json) is dict:
        # It's a dict, we process the values in it
        newjson = {}
        for k in json.keys():
            newjson[k] = preprocessJson(json[k], varData)
        return newjson
    elif type(json) is list:
        # It's a list, we filter the values in it
        newjson = map(lambda x: preprocessJson(x, varData), json)
        # We remove None values, which are probably undefined variables
        while None in newjson:
            newjson.remove(None)
        return newjson
    else:
        return json



def getDefault(defaultParams, field, lang, default):
    """Checks defaultParams for a language-specific field, defaults to the
    non-language-specific field if it's not available."""
    
    if defaultParams.has_key('%s-%s' % (field, lang)):
        return '@%s-%s' % (field, lang)
    elif defaultParams.has_key(field):
        return '@%s' % field
    else:
        return default


def genOneSol(filePath, defaultParams, execParams, solId, lang=None):
    """Make the compilation and execution JSON data for one solution in
    filePath."""
    solName = os.path.basename(filePath)

    # Auto-detect language from extension
    (r, ext) = os.path.splitext(filePath)
    if lang:
        solLang = lang
    elif CFG_LANGEXTS.has_key(ext):
        solLang = CFG_LANGEXTS[ext]
    else:
        raise Exception("Couldn't auto-detect language for `%s`.\nUse '-l' option to specify language." % filePath)

    # Do we have a skeleton for the solution ?
    skeleton = defaultParams.get('defaultSkeleton', {
        'language': '%sollang',
        'files': [{'name': '%solfilename',
                   'path': '%solpath'}],
        'dependencies': '%soldeps'
        })

    # Do we have the defaultDependencies in the defaultParams?
    dep = getDefault(defaultParams, 'defaultDependencies', solLang, [])
    # Do we have the defaultFilterTests in the defaultParams?
    ftests = getDefault(defaultParams, 'defaultFilterTests', solLang, ['*.in'])

    # Fill in the skeleton
    descr = preprocessJson(skeleton, {
        'sollang': solLang,
        'solfilename': os.path.basename(filePath),
        'solpath': filePath,
        'soldeps': dep})

    # Solution compilation
    jsonSolution = {
        'id': 'sol%d-%s' % (solId, solName),
        'compilationDescr': descr,
        'compilationExecution': execParams}

    # Solution execution
    jsonExecution = {
        'id': 'exec%d-%s' % (solId, solName),
        'idSolution': 'sol%d-%s' % (solId, solName),
        'filterTests': ftests,
        'runExecution': execParams}

    return (jsonSolution, jsonExecution)


def genStdTaskJson(taskPath, files, execParams, lang=None):
    """Make a default evaluation JSON, evaluating the solutions in files
    against the task in taskPath, using execParams as constraints for the
    compilation and execution."""

    # Load defaultParams from the task path
    defaultParams = json.load(open(os.path.join(taskPath, 'defaultParams.json'), 'r'))

    testSolutions = []
    testExecutions = []
    # We add the parameters for each solution file given
    for solId, filePath in enumerate(files):
        (jsol, jexc) = genOneSol(filePath, defaultParams, execParams, solId, lang)
        testSolutions.append(jsol)
        testExecutions.append(jexc)

    # Do we have extraTests defined in the defaultParams?
    if defaultParams.has_key('defaultExtraTests'):
        etests = '@defaultExtraTests'
    else:
        etests = []

    # Final evaluation JSON to be given to the taskgrader
    testEvaluation = {
        'rootPath': defaultParams['rootPath'],
        'taskPath': taskPath,
        'generators': ['@defaultGenerator'],
        'generations': ['@defaultGeneration'],
        'extraTests': etests,
        'sanitizer': '@defaultSanitizer',
        'checker': '@defaultChecker',
        'solutions': testSolutions,
        'executions': testExecutions}

    return testEvaluation


if __name__ == '__main__':
    execParams = {}
    execParams.update(CFG_EXECPARAMS)

    # Read command line options
    argParser = argparse.ArgumentParser(description="Make a standard JSON to grade the program(s) in FILE(s) with the taskgrader, using default parameters.")

    argParser.add_argument('files', metavar='FILE', nargs='+', help='Executable to grade; must accept the task on stdin and output the results on stdout')
    argParser.add_argument('-l', '--lang', help="Sets the language of the solution(s)")
    argParser.add_argument('-m', '--memory-limit', type=int, help="Sets the memory limit for compilation and execution, in kilobytes", default=execParams['memoryLimitKb'])
    argParser.add_argument('-t', '--time-limit', type=int, help="Sets the time limit for compilation and execution, in milliseconds", default=execParams['timeLimitMs'])
    argParser.add_argument('-p', '--task-path', help="Sets the task path; defaults to current directory")
    argParser.add_argument('-r', '--real-path', help="Keep given file paths as-is, do not make them absolute", action='store_true')

    args = argParser.parse_args()

    # We default the task path to the current directory if there's a defaultParams in it
    if not args.task_path and os.path.isfile('defaultParams.json'):
        args.task_path = os.getcwd()
    elif not args.task_path or not os.path.isfile(os.path.join(args.task_path, 'defaultParams.json')):
        print "Current directory is not a task and no task path given. Aborting."
        argParser.print_help()
        sys.exit(1)

    # Add command-line given constraints to execParams
    execParams['memoryLimitKb'] = args.memory_limit
    execParams['timeLimitMs'] = args.time_limit

    # By default, we make the paths given on command-line absolute
    if args.real_path:
        files = args.files
    else:
        files = map(lambda f: os.path.join(os.getcwd(), f), args.files)

    # Make the JSON
    print json.dumps(genStdTaskJson(args.task_path, files, execParams, args.lang))
