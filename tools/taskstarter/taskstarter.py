#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This tool helps task writers create and test their tasks.
# It handles simple tasks, and is not suited for tasks using more advanced
# features of the taskgrader.


import argparse, distutils.dir_util, json, os, subprocess, sys

SELFDIR = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))

CFG_GENJSON = os.path.normpath(os.path.join(SELFDIR, '../genJson/genJson.py'))
CFG_STDGRADE = os.path.normpath(os.path.join(SELFDIR, '../stdGrade/stdGrade.sh'))

# subprocess.DEVNULL is only present in python 3.3+.
DEVNULL = open(os.devnull, 'w')

def getTaskSettings(path):
    """Get taskSettings from task path 'path', raise an error if there is no
    taskSettings.json in 'path'."""
    tspath = os.path.join(path, 'taskSettings.json')
    if os.path.isfile(tspath):
        try:
            taskSettings = json.load(open(tspath, 'r'))
        except:
            print("/!\ taskSettings.json does not contain valid JSON data.")
            sys.exit(1)
    else:
        print("/!\ No taskSettings.json file detected, are you in the right folder?")
        sys.exit(1)

    return taskSettings


### Action-handling functions
def init(args):
    """Start a task in destination folder."""
    print("Copying base task files to '%s'..." % args.dest)
    try:
        distutils.dir_util.copy_tree(os.path.join(SELFDIR, 'base'), args.dest)
        print("""Task started at '%s'.
Edit the task files as described inside each file, then use
`%s test` to test your task.""" % (args.dest, os.path.basename(sys.argv[0])))
        return 0
    except:
        print("Error while starting task: %s" % sys.exc_info()[0])
        return 1


def add(args):
    """Add a program."""
    taskSettings = getTaskSettings(args.taskpath)
    progpath = os.path.relpath(args.path, args.taskpath)

    if args.type in taskSettings:
        print("Updating %s from `%s` to `%s`" % (args.type, taskSettings[args.type], args.path))
    else:
        print("Setting %s to `%s`" % (args.type, args.path))
    taskSettings[args.type] = progpath

    # Save new taskSettings
    json.dump(taskSettings, open(os.path.join(args.taskpath, 'taskSettings.json'), 'w'))

    return 0


def addsol(args):
    """Add a correctSolution."""
    taskSettings = getTaskSettings(args.taskpath)
    solpath = '$TASK_PATH/%s' % os.path.relpath(args.path, args.taskpath)

    if 'correctSolutions' not in taskSettings:
        taskSettings['correctSolutions'] = []
    newcs = []
    for cs in taskSettings['correctSolutions']:
        if cs['path'] == solpath:
            if cs['language'] == args.lang and cs['grade'] == args.grade:
                print("Solution `%s` already registered." % args.path)
                newcs = taskSettings['correctSolutions']
                break
            else:
                print("Updating solution `%s` parameters." % args.path)
                # We remove the current entry, it will get re-added with the
                # new parameters
        else:
            newcs.append(cs)
    else:
        newcs.append({'path': solpath,
            'language': args.lang,
            'grade': args.grade})

    taskSettings['correctSolutions'] = newcs

    # Save new taskSettings
    json.dump(taskSettings, open(os.path.join(args.taskpath, 'taskSettings.json'), 'w'))
    print("Added solution `%s` successfully." % args.path)

    return 0

def removesol(args):
    """Remove a correctSolution."""
    taskSettings = getTaskSettings(args.taskpath)

    if 'correctSolutions' not in taskSettings or len(taskSettings['correctSolutions']) == 0:
        print("No correctSolution defined.")
        return 1

    if args.removeall:
        print("Removing all solutions...")
        taskSettings['correctSolutions'] = []
    elif args.path:
        solpath = '$TASK_PATH/%s' % os.path.relpath(args.path, args.taskpath)
        newcs = []
        removed = False
        for cs in taskSettings['correctSolutions']:
            if cs['path'] == solpath:
                removed = True
            else:
                newcs.append(cs)
        if not removed:
            print("Solution not found in correctSolutions.")
            return 1
        taskSettings['correctSolutions'] = newcs
    else:
        print("No solution to remove given.")
        return 1

    # Save new taskSettings
    json.dump(taskSettings, open(os.path.join(args.taskpath, 'taskSettings.json'), 'w'))
    print("Solution(s) removed successfully!")

    return 0


def show(args):
    """Show settings of a task."""
    taskSettings = getTaskSettings(args.taskpath)
    print("Task in folder `%s`:" % args.taskpath)

    if 'correctSolutions' in taskSettings:
        if len(taskSettings['correctSolutions']) > 0:
            print("%d correctSolutions defined:" % len(taskSettings['correctSolutions']))
            for cs in taskSettings['correctSolutions']:
                print("  `%s`, language '%s'" % (cs['path'], cs['language']), end="")
                if 'grade' in cs:
                    print(", expected grade %d" % cs['grade'])
                else:
                    print("")
        else:
            print("No correctSolutions defined.")
        taskSettings.pop('correctSolutions')

    for comp in ['generator', 'sanitizer', 'checker']:
        if comp in taskSettings:
            print("%s: `%s`" % (comp, taskSettings[comp]), end="")
            if "%sDeps" % comp in taskSettings:
                print("with dependencies:")
                for dep in taskSettings["%sDeps" % comp]:
                    print("  %s" % dep)
                taskSettings.pop("%sDeps" % comp)
            else:
                print()
            taskSettings.pop(comp)

    if len(taskSettings.keys()) > 0:
        for k in taskSettings.keys():
            print("%s: %s" % (k, taskSettings[k]))

    return 0


def test(args):
    """Test a task."""
    # Check taskSetting for a correctSolution; if none is set, warn the user
    # about it.
    taskSettings = getTaskSettings(args.taskpath)
    if 'correctSolutions' not in taskSettings:
        print("""/!\ No correctSolutions in taskSettings, the correctness of the task cannot be
tested. We will only test whether the task compiles.\n""")

    # Call genJson, it will take care of checking everything while generating
    # TODO :: better genJson interaction
    print("Calling genJson...")
    if args.verbose:
        proc = subprocess.Popen([CFG_GENJSON, '-v', args.taskpath])
    else:
        proc = subprocess.Popen([CFG_GENJSON, args.taskpath])
    proc.wait()
    print("")
    if proc.returncode > 0:
        print("genJson exited with return code %d, read output to check for errors." % proc.returncode)
    else:
        print("genJson completed successfully, task seems correct.")

    # Exit with the same returncode as genJson
    return proc.returncode


def testsol(args):
    """Test a solution against a task."""
    # User probably expects the defaultParams.json to be updated if he made
    # modifications to his task, so we call genJson first (without output)
    print("Calling genJson...")
    proc = subprocess.Popen([CFG_GENJSON, args.taskpath], stdout=DEVNULL, stderr=DEVNULL)
    proc.wait()

    # If genJson failed, we cannot test
    if proc.returncode > 0:
        print("genJson exited with return code %d, use 'test' action to check the reason" % proc.returncode)
        return proc.returncode

    print("Testing with stdGrade.sh...")
    proc = subprocess.Popen([CFG_STDGRADE, args.path], cwd=args.taskpath)
    proc.wait()
    return proc.returncode


def remotetest(args):
    """Test a task with a remote taskgrader."""
    # TODO
    print("Not yet implemented.")
    return 1


if __name__ == '__main__':
    # Parse command-line arguments
    argParser = argparse.ArgumentParser(description="This tool helps task writers create and test their tasks.")

    # Parsers for each sub-command
    subparsers = argParser.add_subparsers(help='Action', dest='action')

    helpParser = subparsers.add_parser('help', help='Get help on an action')
    helpParser.add_argument('helpaction', help='Action to get help for', nargs='?', metavar='action')

    initParser = subparsers.add_parser('init', help='Start a task', description="""
        The 'init' action will create the base structure for a task with
        example programs. You can then edit these programs to suit your
        task's needs.""")
    initParser.add_argument('dest', help='Destination folder', nargs='?', default='.')

    addParser = subparsers.add_parser('add', help='Add a program to the task', description="""
        The 'add' action allows to specify the paths to each program of the
        task, if different from the default ones. You can setup the path to the
        generator, to the sanitizer, or to the checker with this action.""")
    addParser.add_argument('-t', '--taskpath', help='Task path', default='.')
    addParser.add_argument('type', help='Type of the program', choices=['generator', 'sanitizer', 'checker'])
    addParser.add_argument('path', help='Path to the program')

    addsolParser = subparsers.add_parser('addsol', help='Add a correct solution to the task', description="""
        The 'addsol' action allows to specify a "correct solution" for the
        task. A "correct solution" is a solution that gets an expected grade
        when tested against the task, for instance a solution always giving
        good answers and getting a grade of 100 each time, or a bad solution
        always getting a grade of 0 for each test. Adding a "correct solution"
        allows to test automatically whether the task grades properly the
        solutions.""")
    addsolParser.add_argument('-t', '--taskpath', help='Task path', default='.')
    addsolParser.add_argument('-g', '--grade', help='Expected grade for the solution', type=int, default=100, action='store')
    addsolParser.add_argument('-l', '--lang', help='Language of the solution', required=True, action='store')
    addsolParser.add_argument('path', help='Path to the solution')

    removesolParser = subparsers.add_parser('removesol', help='Remove a correct solution from the task', description="""
        The 'removesol' action allows to remove a "correct solution" which was
        added with 'addsol' from the task.""")
    removesolParser.add_argument('-a', '--all', help='Remove all correct solutions', dest='removeall', action='store_true')
    removesolParser.add_argument('-t', '--taskpath', help='Task path', default='.')
    removesolParser.add_argument('path', help='Path to the solution', nargs='?', default='')

    showParser = subparsers.add_parser('show', help='Show task settings', description="""
        The 'show' action lists the settings of the task.""")
    showParser.add_argument('taskpath', help='Task folder', nargs='?', default='.')

    testParser = subparsers.add_parser('test', help='Test a task with the local taskgrader', description="""
        The 'test' action will test the task with the local taskgrader. It will
        call genJson to generate the `defaultParameters.json` file, which
        describes the task to the taskgrader. It will then try to compile the
        task files with the taskgrader, then test the "correct solutions" with
        the taskgrader, ensuring that all correct solutions get their expected
        grades.""")
    testParser.add_argument('taskpath', help='Task folder', nargs='?', default='.')
    testParser.add_argument('-v', '--verbose', help='Be more verbose', action='store_true')

    testsolParser = subparsers.add_parser('testsol', help='Test a solution with the task', description="""
        The 'testsol' action allows to test a solution with the task. It will
        test with default parameters and give you a summary of the results.""")
    testsolParser.add_argument('-t', '--taskpath', help='Task path', default='.')
    testsolParser.add_argument('path', help='Path to the solution')

    remotetestParser = subparsers.add_parser('remotetest', help='Test a task with a remote taskgrader', description="""
        The 'remotetest' actions does the same test than the 'test' action, but
        uses a remote taskgrader.""")
    remotetestParser.add_argument('taskpath', help='Task folder', nargs='?', default='.')

    args = argParser.parse_args()

    # List of parsers and functions handling each action
    ACTIONS = {
        'init': {'p': initParser, 'f': init},
        'add': {'p': addParser, 'f': add},
        'addsol': {'p': addsolParser, 'f': addsol},
        'removesol': {'p': removesolParser, 'f': removesol},
        'show': {'p': showParser, 'f': show},
        'test': {'p': testParser, 'f': test},
        'testsol': {'p': testsolParser, 'f': testsol},
        'remotetest': {'p': remotetestParser, 'f': remotetest}
        }

    if args.action == 'help':
        if args.helpaction in ACTIONS.keys():
            ACTIONS[args.helpaction]['p'].print_help()
        elif args.helpaction:
            helpParser.error("Action '%s' does not exist." % args.helpaction)
        else:
            argParser.print_help()
    else:
        # Execute the action; each action function returns an exitcode
        sys.exit(ACTIONS[args.action]['f'](args))
