#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This companion tool to the taskgrader makes a default evaluation JSON for the
# program in FILE, using default parameters set in config.py.


import argparse, json, os, sys

from config_default import *
from config import *


def getDefault(defaultParams, field, lang, default):
    """Checks defaultParams for a language-specific field, defaults to the
    non-language-specific field if it's not available."""

    if defaultParams.has_key('%s-%s' % (field, lang)):
        return '@%s-%s' % (field, lang)
    elif defaultParams.has_key(field):
        return '@%s' % field
    else:
        return default


def genStdTaskJson(taskPath, execPath, execParams, lang=None):
    """Make a default evaluation JSON, evaluating the solutions in files
    against the task in taskPath, using execParams as constraints for the
    compilation and execution."""

    # Load defaultParams from the task path
    defaultParams = json.load(open(os.path.join(taskPath, 'defaultParams.json'), 'r'))

    # Auto-detect language from extension
    (r, ext) = os.path.splitext(execPath)
    if lang:
        solLang = lang
    elif CFG_LANGEXTS.has_key(ext):
        solLang = CFG_LANGEXTS[ext]
    else:
        raise Exception("Couldn't auto-detect language for `%s`.\nUse '-l' option to specify language." % execPath)

    # Do we have the defaultDependencies in the defaultParams?
    dep = getDefault(defaultParams, 'defaultDependencies', solLang, [])

    # Parameters of the solution
    extraParams = {
        'solutionLanguage': solLang,
        'solutionFilename': os.path.basename(execPath),
        'solutionPath': execPath,
        'solutionDependencies': dep,
        'defaultSolutionExecParams': execParams
        }

    # Final evaluation JSON to be given to the taskgrader
    testEvaluation = {
        'rootPath': defaultParams['rootPath'],
        'taskPath': os.path.realpath(taskPath),
        'extraParams': extraParams
        }

    return testEvaluation


if __name__ == '__main__':
    execParams = {}
    execParams.update(CFG_EXECPARAMS)

    # Read command line options
    argParser = argparse.ArgumentParser(description="Make a standard JSON to evaluate the program in FILE against a task with the taskgrader, using default parameters.")

    argParser.add_argument('file', metavar='FILE', help='Executable to grade; must accept the task on stdin and output the results on stdout')
    argParser.add_argument('-l', '--lang', help="Sets the language of the solution")
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
        sys.exit(1)

    # Add command-line given constraints to execParams
    execParams['memoryLimitKb'] = args.memory_limit
    execParams['timeLimitMs'] = args.time_limit

    # By default, we make the paths given on command-line absolute
    if args.real_path:
        execPath = args.file
    else:
        execPath = os.path.abspath(args.file)

    # Make the JSON
    print json.dumps(genStdTaskJson(args.task_path, execPath, execParams, args.lang))
