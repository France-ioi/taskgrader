#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT



import argparse, json, os, sys, subprocess
from config import CFG_TASKGRADER, CFG_EXECPARAMS, CFG_LANGEXTS


if __name__ == '__main__':
    execParams = {}
    execParams.update(CFG_EXECPARAMS)

    # Read command line options
    argParser = argparse.ArgumentParser(description="Grades the program(s) in FILE(s) with the taskgrader, using default parameters.")

    argParser.add_argument('files', metavar='FILE', nargs='+', help='Program to grade')
    argParser.add_argument('-d', '--debug', help='Shows all the JSON data generated', action='store_true')
    argParser.add_argument('-m', '--memory-limit', type=int, help="Sets the memory limit for compilation and execution", default=execParams['memoryLimitKb'])
    argParser.add_argument('-t', '--time-limit', type=int, help="Sets the time limit for compilation and execution", default=execParams['timeLimitMs'])
    argParser.add_argument('-p', '--task-path',  help="Sets the task path; defaults to current directory")

    args = argParser.parse_args()

    # We default the task path to the current directory if there's a defaultParams in it
    if not args.task_path and os.path.isfile('defaultParams.json'):
        args.task_path = os.getcwd()
    elif not os.path.isfile(os.path.join(args.task_path, 'defaultParams.json')):
        print "Current directory is not a task and no task path given. Aborting."
        parser.print_help()
        sys.exit(1)

    execParams['memoryLimitKb'] = args.memory_limit
    execParams['timeLimitMs'] = args.time_limit

    print "Running task in %s" % args.task_path

    defaultParams = json.load(open(os.path.join(args.task_path, 'defaultParams.json'), 'r'))

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
        lang = CFG_LANGEXTS[ext]

        print "Adding solution %s, language %s" % (f, lang)

        # Do we have the defaultDependencies in the defaultParams?
        if defaultParams.has_key('defaultDependencies-' + lang):
            dep = '@defaultDependencies-' + lang
        elif defaultParams.has_key('defaultDependencies'):
            dep = '@defaultDependencies'
        else:
            dep = []
        
        # Do we have the defaultFilterTests in the defaultParams?
        if defaultParams.has_key('defaultFilterTests-' + lang):
            ftests = '@defaultFilterTests-' + lang
        elif defaultParams.has_key('defaultFilterTests'):
            ftests = '@defaultFilterTests'
        else:
            ftests = ['*.in']
        

        testSolutions.append({
            'id': 'sol%d-%s' % (solId, solName),
            'compilationDescr': {
                'language': lang,
                'files': [{'name': os.path.basename(f),
                           'path': filePath}],
                'dependencies': dep},
            'compilationExecution': execParams})

        testExecutions.append({
            'id': 'exec%d-%s' % (solId, solName),
            'idSolution': 'sol%d-%s' % (solId, solName),
            'filterTests': ftests,
            'runExecution': execParams})


    # Do we have extraTests defined in the defaultParams?
    if defaultParams.has_key('defaultExtraTests'):
        etests = '@defaultExtraTests'
    else:
        etests = []

    # Final evaluation JSON to be given to the taskgrader
    testEvaluation = {
        'rootPath': defaultParams['rootPath'],
        'taskPath': args.task_path,
        'generators': ['@defaultGenerator'],
        'generations': ['@defaultGeneration'],
        'extraTests': etests,
        'sanitizer': '@defaultSanitizer',
        'checker': '@defaultChecker',
        'solutions': testSolutions,
        'executions': testExecutions}

    if args.debug:
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
            elif report.has_key('execution'):
                # Solution error
                print 'Solution returned an error. Solution report:'
                print json.dumps(report['execution'])
            else:
                # Sanitizer error
                print 'Test rejected by sanitizer. Sanitizer report:'
                print json.dumps(report['sanitizer'])
    if args.debug:
        print ''
        print '* Full report:'
        print json.dumps(resultJson)
