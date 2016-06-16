#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This tool automatically determines the time/memory limits for a task, and the
# time/memory transformation functions for the current server.


import argparse, json, os, sys, subprocess

SELFDIR = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))

CFG_GENSTD = os.path.normpath(os.path.join(SELFDIR, '../stdGrade/genStdTaskJson.py'))
CFG_TASKGRADER = os.path.normpath(os.path.join(SELFDIR, '../../taskgrader.py'))

CFG_RATIO = 0.05 # Ratio which is considered as a good limit
CFG_MAX_TIMELIMIT = 60000       # in milliseconds
CFG_MAX_MEMORYLIMIT = 1024*1024 # in kilobytes


def linearRegression(xyList):
    """Return the coefficients a b so that yList ~= a * xList + b."""
    avgX, avgY, avgX2, avgXY = 0, 0, 0, 0
    for x, y in xyList:
        avgX += x / len(xyList)
        avgY += y / len(xyList)
        avgX2 += x**2 / len(xyList)
        avgXY += x*y / len(xyList)
    a = (avgXY - avgX * avgY) / (avgX2 - avgX**2)
    b = avgY - a * avgX

    return (int(a), int(b))


def tryEvaluation(taskPath, solution, timeLimit=None, memoryLimit=None, language=None):
    """Evaluate a solution against a task, using specified limits.
    If limits are None, the default limits set for the task are used."""

    # Prepare genStdTaskJson arguments
    genCmd = [CFG_GENSTD, '-p', taskPath, '-r', solution]
    if timeLimit is not None:
        genCmd.extend(['-t', str(timeLimit)])
    if memoryLimit is not None:
        genCmd.extend(['-m', str(memoryLimit)])
    if language is not None:
        genCmd.extend(['-l', language])

    # Launch an evaluation
    genProc = subprocess.Popen(genCmd, stdout=subprocess.PIPE, universal_newlines=True)
    graderProc = subprocess.Popen([CFG_TASKGRADER], stdin=genProc.stdout, stdout=subprocess.PIPE, universal_newlines=True)

    try:
        outputJson = json.load(graderProc.stdout)
    except:
        raise Exception("Evaluation failed for solution '%s' with task '%s'." % (solution, taskPath))

    # Read usage
    maxTime = 0
    maxMem = 0
    maxTimeLimit = 0
    maxMemLimit = 0
    nbFails, nbNoExec, nbTotal = 0, 0, 0

    for execution in outputJson['executions']:
        for testReport in execution['testsReports']:
            nbTotal += 1
            # We skip tests where the solution was not executed
            if 'execution' not in testReport:
                nbNoExec += 1
                continue

            execReport = testReport['execution']
            if execReport['exitCode'] > 0:
                nbFails += 1
            else:
                maxTime = max(maxTime, execReport['timeTakenMs'])
                maxMem = max(maxMem, execReport['memoryUsedKb'])
                maxTimeLimit = max(maxTimeLimit, execReport['timeLimitMs'])
                maxMemLimit = max(maxMemLimit, execReport['memoryLimitKb'])

    # Return whether there were failures, the maximum time taken and the maximum memory used
    return {'failed': nbFails > 0,
            'maxTime': maxTime,
            'maxMem': maxMem,
            'maxTimeLimit': maxTimeLimit,
            'maxMemLimit': maxMemLimit}


def tryMultipleEvaluations(taskPath, solutionList, timeLimit=None, memoryLimit=None, language=None):
    """Evaluate multiple solutions against a task, summarizing the results."""
    # Evaluate each solution individually
    reports = []
    for solution in solutionList:
        reports.append(tryEvaluation(taskPath, solution, timeLimit, memoryLimit, language))

    # Fetch values from each report
    finalReport = {}
    finalReport['failed'] = any(map(lambda r: r['failed'], reports))
    for key in ['maxTime', 'maxMem', 'maxTimeLimit', 'maxMemLimit']:
        finalReport[key] = max(map(lambda r: r[key], reports))

    return finalReport


def findLimits(taskPath, solutionList, language=None):
    """Find good limits for a task, encompassing solutions from solutionList."""
    minTimeLimit = 0
    maxTimeLimit = CFG_MAX_TIMELIMIT
    minMemLimit = 0
    maxMemLimit = CFG_MAX_MEMORYLIMIT

    tlOk = False
    mlOk = False

    # Do a first evaluation to get the task's default limits
    print("Initial evaluation...")
    taskEval = tryMultipleEvaluations(taskPath, solutionList)
    if taskEval['failed']:
        minTimeLimit = taskEval['maxTimeLimit']
        minMemLimit = taskEval['maxMemLimit']
    else:
        maxTimeLimit = taskEval['maxTimeLimit']
        maxMemLimit = taskEval['maxMemLimit']

    print("Finding time limit", end='', flush=True)
    while True:
        # Check if limits are under ratio
        if maxTimeLimit <= 0 or maxTimeLimit - minTimeLimit < CFG_RATIO * maxTimeLimit:
            break

        curTimeLimit = int((minTimeLimit + maxTimeLimit) / 2)

        # Make new evaluations
        curEval = tryMultipleEvaluations(taskPath, solutionList, timeLimit=curTimeLimit, memoryLimit=maxMemLimit, language=language)

        # Check if evaluation was successful or failed
        if curEval['failed']:
            minTimeLimit = curTimeLimit + 1
            print('!', end='', flush=True)
        else:
            maxTimeLimit = curTimeLimit
            print('.', end='', flush=True)
    print(' done.')

    print("Finding memory limit", end='', flush=True)
    while True:
        # Check if limits are under ratio
        if maxMemLimit <= 0 or maxMemLimit - minMemLimit < CFG_RATIO * maxMemLimit:
            # We're done
            break

        curMemLimit = int((minMemLimit + maxMemLimit) / 2)

        # Make new evaluations
        curEval = tryMultipleEvaluations(taskPath, solutionList, timeLimit=maxTimeLimit, memoryLimit=curMemLimit, language=language)

        # Check if evaluation was successful or failed
        if curEval['failed']:
            minMemLimit = curMemLimit + 1
            print('!', end='', flush=True)
        else:
            maxMemLimit = curMemLimit
            print('.', end='', flush=True)
    print(' done.')

    # Last evaluation to get the maxTime and maxMem
    finalEval = tryMultipleEvaluations(taskPath, solutionList, timeLimit=maxTimeLimit, memoryLimit=maxMemLimit)

    return {
        'maxTimeLimit': maxTimeLimit,
        'maxMemLimit': maxMemLimit,
        'maxTime': finalEval['maxTime'],
        'maxMem': finalEval['maxMem']
        }

def configLang(reference, lang):
    """Find the limit transformations to apply globally for the specified
    language."""
    progsPath = os.path.join(SELFDIR, 'programs/')

    timeList = []
    memList = []
    for solution in reference[lang]:
        print("* Evaluating '%s' for language '%s'" % (solution['name'], lang))
        results = findLimits(progsPath, [os.path.join(progsPath, solution['name'])], language=lang)
        print("Time: %dms (ref: %dms) / Memory: %dKb (ref: %dKb)" % (
            results['maxTimeLimit'], solution['time'],
            results['maxMemLimit'], solution['memory']))

        timeList.append((solution['time'], results['maxTimeLimit']))
        memList.append((solution['memory'], results['maxMemLimit']))

    timeA, timeB = linearRegression(timeList)
    memA, memB = linearRegression(memList)
    print("""
Results for language '%s':
Time transformation: lambda x: %d * x + %d
Memory transformation: lambda x: %d * x + %d
""" % (lang, timeA, timeB, memA, memB))


### Actions
def config(args):
    """Find the limit transformations to apply globally."""
    print("/!\ The reference limits aren't set yet.") # TODO :: remove once reference.json is populated
    reference = json.load(open(os.path.join(SELFDIR, 'reference.json'), 'r'))
    # Language specified on the command-line
    if args.lang:
        if args.lang not in reference:
            print("Error: language '%s' has no reference limits." % args.lang)
            return 1
        configLang(reference, args.lang)
        return 0

    # We do all languages
    for lang in reference:
        configLang(reference, lang)

    return 0


def task(args):
    """Find the adequate limits for a task."""
    solutionList = args.path[:]
    if args.usecorrect or len(args.path) == 0:
        try:
            taskSettings = json.load(open(os.path.join(args.taskpath, 'taskSettings.json'), 'r'))
            correctSolutions = taskSettings['correctSolutions']
            solutionList.extend(map(lambda c: c['path'].replace('$TASK_PATH', args.taskpath), correctSolutions))
        except:
            print("Warning: unable to add correctSolutions.")

    if len(solutionList) == 0:
        print("Error: no solutionList given on command-line, and no correctSolutions added.")
        return 1

    print("Searching limits with %d solutions." % len(solutionList))
    results = findLimits(args.taskpath, solutionList)
    print("""
Limits found:
Time: %(maxTimeLimit)dms / Memory: %(maxMemLimit)dKb
(maximum time used: %(maxTime)dms, memory used: %(maxMem)dKb)""" % results)

    return 0

if __name__ == '__main__':
    # Parse command-line arguments
    argParser = argparse.ArgumentParser(description="This tool finds the adequate limits for general evaluations and tasks.")

    # Parsers for each sub-command
    subparsers = argParser.add_subparsers(help='Action', dest='action')

    helpParser = subparsers.add_parser('help', help='Get help on an action')
    helpParser.add_argument('helpaction', help='Action to get help for', nargs='?', metavar='action')

    configParser = subparsers.add_parser('config', help='Find global transformation functions', description="""
        Find the limits for the reference task and solution, to determine which
        transformation functions should be set in taskgrader's configuration.""")
    configParser.add_argument('-l', '--lang', help='Only determine for this language')

    taskParser = subparsers.add_parser('task', help='Find limits for a task', description="""
        Find good time and memory limits for a task, testing on which limits
        the solutions given can't execute anymore.""")
    taskParser.add_argument('-c', '--usecorrect', help='Use task correctSolutions', action='store_true')
    taskParser.add_argument('-t', '--taskpath', help='Task path', default='.')
    taskParser.add_argument('path', help='Paths of solutions to test', nargs='*')

    args = argParser.parse_args()

    # List of parsers and functions handling each action
    ACTIONS = {
        'config': {'p': configParser, 'f': config},
        'task': {'p': taskParser, 'f': task}
        }

    if args.action == 'help':
        if args.helpaction in ACTIONS.keys():
            ACTIONS[args.helpaction]['p'].print_help()
        elif args.helpaction:
            helpParser.error("Action '%s' does not exist." % args.helpaction)
        else:
            argParser.print_help()
    elif args.action:
        # Execute the action; each action function returns an exitcode
        sys.exit(ACTIONS[args.action]['f'](args))
    else:
        argParser.print_help()
