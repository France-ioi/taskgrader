#!/usr/bin/env python
# -*- coding: utf-8 -*-

### Programme d'évaluation des solutions de France-IOI

# Copyright (c) 2015 France-IOI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.



import getopt
# Usual imports
import glob, hashlib, json, os, random, shlex, shutil, sys, subprocess

# Taskgrader path
CFG_TASKGRADER = '/home/michel/franceioi/taskgrader/taskgrader.py'
# Default solution compilation and execution parameters
CFG_EXECPARAMS = {'timeLimitMs': 60000,
                  'memoryLimitKb': 128*1024,
                  'useCache': True,
                  'stdoutTruncateKb': -1,
                  'stderrTruncateKb': -1,
                  'getFiles': []}
# Languages supported, file extension -> language
CFG_LANGUAGES = {'.c': 'c',
                 '.cpp': 'cpp',
                 '.py': 'py',
                 '.ml': 'ocaml',
                 '.java': 'java',
                 '.pas': 'pascal',
                 '.sh': 'sh',
                 '': 'sh'}


if __name__ == '__main__':
    execParams = {}
    execParams.update(CFG_EXECPARAMS)
    debug = False

    # We default the task path to the current directory if there's a defaultParams in it
    if os.path.isfile('defaultParams.json'):
        taskPath = os.getcwd()
    else:
        taskPath = None

    # Read command line options
    try:
        (opts, files) = getopt.getopt(sys.argv[1:], 'dm:t:p:', ['debug', 'memory-limit=', 'time-limit=', 'task-path='])
    except getopt.GetOptError as err:
        print str(err)
        sys.exit(1)
    for (opt, arg) in opts:
        if opt in ['-d', '--debug']:
            debug = True
        elif opt in ['-m', '--memory-limit']:
            execParams['memoryLimitKb'] = int(arg)
        elif opt in ['-t', '--time-limit']:
            execParams['timeLimitMs'] = int(arg)
        elif opt in ['-p', '--task-path']:
            taskPath = arg

    if not taskPath or not os.path.isfile(os.path.join(taskPath, 'defaultParams.json')):
        print "Current directory is not a task and no task path given. Aborting."
        sys.exit(1)

    print "Running task in %s" % taskPath

    defaultParams = json.load(open(os.path.join(taskPath, 'defaultParams.json'), 'r'))

    solId = 0
    testSolutions = []
    testExecutions = []
    # We add the parameters for each solution file given
    for f in files:
        filePath = os.path.join(os.getcwd(), f)
        solName = os.path.basename(f)
        solId += 1

        # Auto-detect language from extension
        (r, ext) = os.path.splitext(f)
        lang = CFG_LANGUAGES[ext]

        print "Adding solution %s, language %s" % (f, lang)

        testSolutions.append({
            'id': 'sol%d-%s' % (solId, solName),
            'compilationDescr': {
                'language': lang,
                'files': [{'name': os.path.basename(f),
                           'path': filePath}],
                'dependencies': '@defaultDependencies-' + lang},
            'compilationExecution': execParams})

        testExecutions.append({
            'id': 'exec%d-%s' % (solId, solName),
            'idSolution': 'sol%d-%s' % (solId, solName),
            'filterTests': '@defaultFilterTests-' + lang,
            'runExecution': execParams})

    # Final evaluation JSON to be given to the taskgrader
    testEvaluation = {
        'rootPath': defaultParams['rootPath'],
        'taskPath': taskPath,
        'generators': ['@defaultGenerator'],
        'generations': ['@defaultGeneration'],
        'extraTests': '@defaultExtraTests',
        'sanitizer': '@defaultSanitizer',
        'checker': '@defaultChecker',
        'solutions': testSolutions,
        'executions': testExecutions}

    if debug:
        print ''
        print '* JSON sent to taskgrader:'
        print json.dumps(testEvaluation)

    # Send to taskgrader
    print ''
    print '* Output from taskgrader'
    proc = subprocess.Popen(['/usr/bin/python', CFG_TASKGRADER], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    (procOut, procErr) = proc.communicate(input=json.dumps(testEvaluation))
    print ''

    print '* Results'
    resultJson = json.loads(procOut)
    for execution in resultJson['executions']:
        print ' * Execution %s:' % execution['name']
        for report in execution['testsReports']:
            if report.has_key('checker'):
                # Everything was executed
                print 'Solution executed successfully. Checker report:'
                print report['checker']['stdout']['data']
            elif report.has_key('solution'):
                # Solution error
                print 'Solution returned an error. Solution report:'
                print json.dumps(report['solution'])
            else:
                # Sanitizer error
                print 'Test rejected by sanitizer. Sanitizer report:'
                print json.dumps(report['sanitizer'])
    if debug:
        print ''
        print '* Full report:'
        print json.dumps(resultJson)
