#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This tool helps task writers create and test their tasks.
# It handles simple tasks, and is not suited for tasks using more advanced
# features of the taskgrader.


import argparse, distutils.dir_util, json, os, shutil, subprocess, sys

SELFDIR = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))

CFG_GENJSON = os.path.normpath(os.path.join(SELFDIR, '../genJson/genJson.py'))
CFG_MAKESTD = os.path.normpath(os.path.join(SELFDIR, '../makeStandaloneJson.py'))
CFG_REMOTE = os.path.normpath(os.path.join(SELFDIR, '../remoteGrader/remoteGrader.py'))

CFG_STDGRADE = os.path.normpath(os.path.join(SELFDIR, '../stdGrade/stdGrade.sh'))
CFG_GENSTD = os.path.normpath(os.path.join(SELFDIR, '../stdGrade/genStdTaskJson.py'))
CFG_SUMRES = os.path.normpath(os.path.join(SELFDIR, '../stdGrade/summarizeResults.py'))

# subprocess.DEVNULL is only present in python 3.3+.
DEVNULL = open(os.devnull, 'w')

# Available scripts for taskstarter init
SCRIPTS = {
    'generator': ('gen.sh', 'tests/gen/gen.sh'),
    'test01.in': ('test01.in', 'tests/files/test01.in'),
    'test01.out': ('test01.out', 'tests/files/test01.out'),
    'sanitizer': {
        'cpp': ('sanitizer.cpp', 'tests/gen/sanitizer.cpp'),
        'python': ('sanitizer.py', 'tests/gen/sanitizer.py')
        },
    'checker': {
        'cpp': ('checker.cpp', 'tests/gen/checker.cpp'),
        'python': ('checker.py', 'tests/gen/checker.py')
        }
    }

def getTaskSettings(args):
    """Get taskSettings from task path 'path', raise an error if there is no
    taskSettings.json in 'path'."""
    tspath = os.path.join(args.taskpath, 'taskSettings.json')
    if os.path.isfile(tspath):
        try:
            taskSettings = json.load(open(tspath, 'r'))
        except:
            print("/!\ taskSettings.json does not contain valid JSON data.")
            if args.force:
                taskSettings = {}
            else:
                sys.exit(1)
    else:
        print("/!\ No taskSettings.json file detected, are you in the right folder?")
        if args.force:
            taskSettings = {}
        else:
            sys.exit(1)

    return taskSettings


def askQuestionBool(prompt):
    """Ask a question, return a boolean corresponding to the answer."""
    answer = input("%s [y/N] " % prompt)
    return (answer.lower() in ['y', 'yes'])

def askQuestionList(prompt, choices):
    """Ask a question with multiple choices, return the choice."""
    while True:
        answer = input("%s [%s] " % (prompt, '/'.join(choices)))
        if answer.lower() in choices:
            return answer.lower()
        else:
            print("Invalid choices. Please select one of the choices: " + ', '.join(choices))

def saveComponent(dest, info):
    """Copies a script from taskstarter's default scripts onto the target
    task directory."""
    # Load information about the script
    scriptName, scriptDest = info
    # Create folders if needed
    destPath = os.path.join(args.dest, scriptDest)
    try:
        os.makedirs(os.path.dirname(destPath))
    except:
        pass
    shutil.copy(os.path.join(SELFDIR, 'scripts', scriptName), destPath)

def checkEditMe(path):
    """Recursively check files for an EDIT ME marker, which is present in all
    taskstarter init scripts."""
    fileList = os.listdir(path)
    fileList.sort()
    foundMarker = False
    # Explore recursively the files in the path
    for f in fileList:
        itemPath = os.path.join(path, f)
        if os.path.isdir(itemPath):
            foundMarker = foundMarker or checkEditMe(itemPath)
        else:
            try:
                for l in open(itemPath, 'r'):
                    if "EDIT ME" in l:
                        foundMarker = True
                        print("EDIT ME marker in file `%s`" % itemPath)
            except:
                pass
    return foundMarker

def checkSvn(path):
    """Check, if the folder is versioned with SVN, that all files have been
    committed."""
    proc = subprocess.Popen(['/usr/bin/svn', 'status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    procOut, procErr = proc.communicate()

    warningDisplayed = False

    for line in procOut.splitlines():
        linePath = line[8:]
        if not linePath:
            # Not a status line, we're done with the main status elements
            return 0
        lineStatus = line[0]
        lineFile = os.path.basename(linePath)

        # Excluded filenames
        if lineFile in ['defaultParams.json', 'testSelect.json']:
            continue

        # Excluded statuses
        if lineStatus in [' ', 'I']:
            continue

        if not warningDisplayed:
            print("\n/!\ Warning: some modifications have not yet been committed to the SVN:")
            warningDisplayed = True

        if lineStatus in ['A', '?', 'R']:
            print("not added: %s" % linePath)
        elif lineStatus in ['D', '!']:
            print("not removed: %s" % linePath)
        else:
            print("modified (%s): %s" % (lineStatus, linePath))

    return 0


### Action-handling functions
def init(args):
    """Start a task in destination folder. taskstarter will ask various
    questions to know which components to add to the task."""
    print("Starting task at `%s`..." % args.dest)
    if args.dest != '.':
        if os.path.isdir(args.dest):
            print("Folder `%s` already exists." % args.dest)
            if not askQuestionBool("Are you sure you want to start a task there?"):
                print("Aborting.")
                return 1
        else:
            try:
                os.makedirs(args.dest)
            except:
                print("Unable to create folder `%s`. Aborting." % args.dest)
                return 1

    answers = {}
    print("""
A task has multiple components, some of which are optional. This tool will now
ask a few questions about which components you need.
Note that the sanitizer and checker can be (for most tasks) written in any
supported language; they don't need to be in the same language than the
solutions evaluated.""")

    # Generator
    print("""
== Generator ==
Test cases are the input files used to evaluate the solutions.
They can be either generated by a script, either stored directly in the task.
Note that the generator is always a shell script.""")
    answers['generator'] = askQuestionBool("Do you want to use a generator to generate the input files?")
    if answers['generator']:
        print("The script `%s` will be added to your task." % SCRIPTS['generator'][1])
    else:
        print("You will need to write the test files directly into the task.")

    # Sanitizer
    print("""
== Sanitizer ==
A sanitizer checks whether the test cases are in the correct format before
using them to evaluate a solution. It is recommended to have one, but it is
optional.""")
    answers['sanitizer'] = askQuestionBool("Do you want to use a sanitizer?")
    if answers['sanitizer']:
        answers['sanitizerLang'] = askQuestionList(
            "In which language do you want to write the sanitizer?",
            list(SCRIPTS['sanitizer'].keys()) + ['other'])
        if answers['sanitizerLang'] == 'other':
            print("""
You will need to write the sanitizer in a language supported by the taskgrader,
and then add it to the task with
  taskstarter.py add sanitizer path/to/sanitizer.ext""")
            answers['sanitizer'] = False
        else:
            print("The script `%s` will be added to your task." % SCRIPTS['sanitizer'][answers['sanitizerLang']][1])

    # Checker
    print("""
== Checker ==
A checker grades the solution from its output for each test case. A checker
made specifically for the task is useful for an actual check of the solution's
answer, but also when there are multiple possible answers, or to give more
precise grades in the case of partially right answers.
If no checker is written, a default one will be used; you will need to write
the expected outputs for each test case.""")
    answers['checker'] = askQuestionBool("Do you want to use a checker?")
    if answers['checker']:
        answers['checkerLang'] = askQuestionList(
            "In which language do you want to write the checker?",
            list(SCRIPTS['checker'].keys()) + ['other'])
        if answers['checkerLang'] == 'other':
            print("""
You will need to write the checker in a language supported by the taskgrader,
and then add it to the task with
  taskstarter.py add checker path/to/checker.ext""")
            answers['checker'] = False
        else:
            print("The script `%s` will be added to your task." % SCRIPTS['checker'][answers['checkerLang']][1])
    # End of questions

    # Create the task
    print("""
Saving the task components...""")

    # Create folders (even if they end up empty)
    for folder in ['tests/files', 'tests/gen']:
        try:
            os.makedirs(os.path.join(args.dest, folder))
        except:
            pass

    # Copy files to the task according to answers and prepare taskSettings
    taskSettings = {}
    if answers['generator']:
        saveComponent(args.dest, SCRIPTS['generator'])
        taskSettings['generator'] = '$TASK_PATH/%s' % SCRIPTS['generator'][1]
    else:
        # No generator, test cases have to be added manually
        saveComponent(args.dest, SCRIPTS['test01.in'])
        if not answers['checker']:
            saveComponent(args.dest, SCRIPTS['test01.out'])

    if answers['sanitizer']:
        saveComponent(args.dest, SCRIPTS['sanitizer'][answers['sanitizerLang']])
        taskSettings['sanitizer'] = '$TASK_PATH/%s' % SCRIPTS['sanitizer'][answers['sanitizerLang']][1]
    if answers['checker']:
        saveComponent(args.dest, SCRIPTS['checker'][answers['checkerLang']])
        taskSettings['checker'] = '$TASK_PATH/%s' % SCRIPTS['checker'][answers['checkerLang']][1]

    # Save new taskSettings
    json.dump(taskSettings, open(os.path.join(args.dest, 'taskSettings.json'), 'w'))

    print("""
Started the task successfully.
Edit the various files which were created, and then run
  taskstarter.py test
to test the task. For more information, read the documentation in the folder
'docs' of the taskgrader repository, or online at the address
http://france-ioi.github.io/taskgrader/ .""")


def add(args):
    """Add a program."""
    taskSettings = getTaskSettings(args)
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
    taskSettings = getTaskSettings(args)
    solpath = '$TASK_PATH/%s' % os.path.relpath(args.path, args.taskpath)

    if 'correctSolutions' not in taskSettings:
        taskSettings['correctSolutions'] = []
    newcs = []
    for cs in taskSettings['correctSolutions']:
        if cs['path'] == solpath:
            if cs.get('language', None) == args.lang and (args.grade is None or cs.get('grade', None) == args.grade):
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
        entry = {'path': solpath,
            'language': args.lang}
        if args.grade:
            entry['grade'] = args.grade
        newcs.append(entry)

    taskSettings['correctSolutions'] = newcs

    # Save new taskSettings
    json.dump(taskSettings, open(os.path.join(args.taskpath, 'taskSettings.json'), 'w'))
    print("Added solution `%s` successfully." % args.path)

    return 0

def removesol(args):
    """Remove a correctSolution."""
    taskSettings = getTaskSettings(args)

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
    taskSettings = getTaskSettings(args)
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
    taskSettings = getTaskSettings(args)

    # Check there is no EDIT ME marker in files
    if checkEditMe(args.taskpath):
        if args.force:
            print("Please edit these files or remove the EDIT ME marker.")
            print("Force option used, testing anyway...")
        else:
            print("Please edit these files or remove the EDIT ME marker before continuing.")
            print("(You can force the test by using the -f switch.)")
            return 1

    if 'correctSolutions' not in taskSettings:
        print("""/!\ No correctSolutions in taskSettings, the correctness of the task cannot be
tested. We will only test whether the task compiles.\n""")

    # Call genJson, it will take care of checking everything while generating
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
        checkSvn(args.taskpath)

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
        print("genJson exited with return code %d, use 'test' action to check the reason." % proc.returncode)
        if proc.returncode == 2:
            print("Non-fatal genJson error, testing the solution anyway.")
        elif args.force:
            print("-f option used, testing the solution anyway.")
        else:
            print("Test cancelled because of genJson error.\nYou can force the test by using the -f switch.")
            return proc.returncode

    print("\nTesting with stdGrade.sh...")
    proc = subprocess.Popen([CFG_STDGRADE, args.path], cwd=args.taskpath)
    proc.wait()
    return proc.returncode


def remotetest(args):
    """Test a task with a remote taskgrader."""
    # User probably expects the defaultParams.json to be updated if he made
    # modifications to his task, so we call genJson first (without output)
    # We also use genJson's test evaluation.
    if not args.getjob:
        print("Calling genJson...")
        proc = subprocess.Popen([CFG_GENJSON, args.taskpath], stdout=DEVNULL, stderr=DEVNULL)
        proc.wait()

    # If genJson failed, we cannot test
    if not args.getjob and proc.returncode > 0:
        print("genJson exited with return code %d, use 'test' action to check the reason." % proc.returncode)
        if proc.returncode == 2:
            print("Non-fatal genJson error, performing remotetest anyway.\n")
        elif args.force:
            print("-f option used, performing remotetest anyway.\n")
        else:
            print("Test cancelled because of genJson error.\nYou can force the test by using the -f switch.")
            return proc.returncode

    # Basically do the same as stdGrade.sh, but using the remoteGrader
    if args.getjob:
        print("Resuming test with remote taskgrader...")
        # Try fetching the job again
        resProc = subprocess.Popen([CFG_REMOTE, '-g', str(args.getjob)], stdout=subprocess.PIPE, universal_newlines=True)
    else:
        print("Testing with remote taskgrader...")
        svnTarget = None
        if args.simple:
            # Try to fetch SVN version information
            # We don't fetch if the JSON sent is full as in that case we don't
            # need to update the SVN repository
            try:
                svnv = subprocess.check_output(['/usr/bin/svnversion', args.taskpath], universal_newlines=True)
                if 'M' in svnv:
                    print("Task was not committed into the SVN repository.")
                    if not askQuestionBool("Continue anyway?"):
                        print("Aborting.")
                        return 1
                else:
                    svnTarget = ''
                    for c in svnv.strip():
                        if c.isdigit():
                            svnTarget += c
                        elif c not in ['M', 'P']:
                            # It's not all digits, it indicates that not all files
                            # are in the same revision
                            svnTarget = None
                            break
            except:
                pass

        # Generate the input JSON
        genProc = subprocess.Popen([CFG_GENSTD, '-p', args.taskpath, '-r', args.path], stdout=subprocess.PIPE, universal_newlines=True)
        if args.simple:
            remInput = genProc.stdout
        else:
            # Make it standalone
            stdProc = subprocess.Popen([CFG_MAKESTD], stdin=genProc.stdout, stdout=subprocess.PIPE, universal_newlines=True)
            remInput = stdProc.stdout
        # Send to the remoteGrader
        resCmd = [CFG_REMOTE]
        if svnTarget is not None:
            resCmd.extend(['-r', svnTarget])
        resProc = subprocess.Popen(resCmd, stdin=remInput, stdout=subprocess.PIPE, universal_newlines=True)
    # Feed the results to summarizeResults
    sumProc = subprocess.Popen([CFG_SUMRES], stdin=resProc.stdout, universal_newlines=True)

    # Wait for all programs to finish
    resProc.wait()
    sumProc.wait()

    return resProc.returncode


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
        task. A "correct solution" is a solution that gets an expected average
        grade when tested against the task, for instance a solution always
        giving good answers and getting a grade of 100 each time, or a bad
        solution sometimes getting a grade of 0 for a test and having a final
        average grade of 25. Adding a "correct solution" allows to test
        automatically whether the task grades properly the solutions.""")
    addsolParser.add_argument('-t', '--taskpath', help='Task path', default='.')
    addsolParser.add_argument('-g', '--grade', help='Expected average grade for the solution', type=int, action='store')
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
    testParser.add_argument('-f', '--force', help='Force test', action='store_true')
    testParser.add_argument('-v', '--verbose', help='Be more verbose', action='store_true')

    testsolParser = subparsers.add_parser('testsol', help='Test a solution with the task', description="""
        The 'testsol' action allows to test a solution with the task. It will
        test with default parameters and give you a summary of the results.""")
    testsolParser.add_argument('-f', '--force', help='Force test', action='store_true')
    testsolParser.add_argument('-t', '--taskpath', help='Task path', default='.')
    testsolParser.add_argument('path', help='Path to the solution')

    remotetestParser = subparsers.add_parser('remotetest', help='Test a task with a remote taskgrader', description="""
        The 'remotetest' actions does the same test than the 'test' action, but
        uses a remote taskgrader.""")
    remotetestParser.add_argument('-f', '--force', help='Force test', action='store_true')
    remotetestParser.add_argument('-g', '--getjob', help='Try to resume a remotetest sent as jobid ID', action='store', metavar='ID', type=int)
    remotetestParser.add_argument('-s', '--simple', help='Send a simple JSON (do not make a full JSON)', action='store_true')
    remotetestParser.add_argument('-t', '--taskpath', help='Task path', default='.')
    remotetestParser.add_argument('path', help='Path to the solution')

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
    elif args.action:
        # Execute the action; each action function returns an exitcode
        sys.exit(ACTIONS[args.action]['f'](args))
    else:
        argParser.print_help()
