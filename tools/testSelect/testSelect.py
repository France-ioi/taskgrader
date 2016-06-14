#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This tool select a minimal set of tests finding errors in each solution.


import argparse, glob, json, os, shutil, subprocess, sys

SELFDIR = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))

CFG_TASKGRADER = os.path.join(SELFDIR, '../../', 'taskgrader.py')


def checkData(args, data):
    """Check integrity of data."""
    # Remove testCases and solutions which don't exist anymore
    testCasesNames = []
    for case in data['testCases'][:]:
        if case.get('path', None) and not os.path.isfile(os.path.join(args.taskpath, case['path'])):
            print("Removing old test case '%s'." % case['name'])
            data['testCases'].remove(case)
        else:
            testCasesNames.append(case['name'])

    solutionNames = []
    for solution in data['solutions'][:]:
        if solution.get('path', None) and not os.path.isfile(os.path.join(args.taskpath, solution['path'])):
            print("Removing old solution '%s'." % solution['name'])
            data['solutions'].remove(solution)
        else:
            solutionNames.append(solution['name'])

    # Remove coverage for pairs which aren't here anymore
    for covSolKey in list(data['coverage'].keys()):
        if covSolKey in solutionNames:
            for covTestKey in list(data['coverage'][covSolKey].keys()):
                if covTestKey not in testCasesNames:
                    del data['coverage'][covSolKey][covTestKey]
        else:
            del data['coverage'][covSolKey]

    # Remove selected tests which aren't in the data anymore
    data['selected'] = list(filter(lambda c: c in testCasesNames, data['selected']))

    return data

def loadData(args):
    """Load testSelect data from the task."""
    # Load testSelect.json
    try:
        data = json.load(open(os.path.join(args.taskpath, 'testSelect.json')))
    except:
        print("Warning: no testSelect data in current folder, using new empty data.")
        data = {
            'solutions': [],
            'testCases': [],
            'coverage': {},
            'selected': []
            }

    return checkData(args, data)

def saveData(args, data):
    """Save testSelect data to the task."""
    try:
        json.dump(
            data,
            open(os.path.join(args.taskpath, 'testSelect.json'), 'w'),
            indent=2,
            sort_keys=True)
    except:
        print("Error saving testSelect data.")
        return 1
    return 0


def makeEvaluationJson(taskPath, solution, casesToTest):
    """Make the evaluation JSON for solution with casesToTest."""
    # Try to load defaultParams
    try:
        defaultParams = json.load(open(os.path.join(taskPath, 'defaultParams.json'), 'r'))
    except:
        defaultParams = {}

    # Solution information
    extraParams = {
        'solutionLanguage': solution['language'],
        'solutionFilename': solution['name'],
        }
    if solution.get('path', None):
        extraParams['solutionPath'] = os.path.abspath(os.path.join(args.taskpath, solution['path']))
    else:
        extraParams['solutionContent'] = solution['content']

    # Test cases information
    extraTests = []
    filterTests = []
    for case in casesToTest.values():
        ncName = 'ts-%s' % case['name']
        if ncName[-3:] != '.in':
            ncName = '%s.in' % ncName
        newCase = {'name': ncName}

        if case.get('path', None):
            newCase['path'] = os.path.abspath(case['path'])
        else:
            newCase['content'] = case['content']

        extraTests.append(newCase)
        filterTests.append(ncName)

    extraParams['defaultFilterTests'] = filterTests

    # Final test evaluation data
    testEvaluation = {
        'rootPath': defaultParams.get('rootPath', '/'),
        'taskPath': os.path.abspath(taskPath),
        'extraTests': extraTests,
        'extraParams': extraParams
        }

    return testEvaluation


def testComplexity(case, taskPath):
    """Compute the 'complexity' of a test case, here its length."""
    if case.get('path', None):
        data = open(os.path.join(taskPath, case['path']), 'r').read()
    else:
        data = case['content']

    return len(data)


def greedyCover(testCases, testCov, testCompl, solSet):
    """Find an approximation of the smallest set cover (greedy algorithm)."""
    # Copy variables to avoid side effects
    curSet = solSet.copy()
    remCases = testCases[:]
    curCov = {}
    for case in testCases:
        curCov[case] = testCov[case].copy()

    selectedCases = []
    while len(curSet) > 0:
        # Find the case covering the largest number of remaining solutions
        maxElems = 0
        caseCandidates = []
        for case in remCases:
            if len(curCov[case]) > maxElems:
                maxElems = len(curCov[case])
                caseCandidates = [case]
            elif len(curCov[case]) == maxElems:
                caseCandidates.append(case)
        selCase = sorted(caseCandidates, key=lambda c: testCompl[c])[-1]

        # Select this case
        selectedCases.append(selCase)
        # Compute new sets, excluding elements already covered
        curSet = curSet - curCov[selCase]
        remCases.remove(selCase)
        for case in remCases:
            curCov[case] = curCov[case] - curCov[selCase]

    return (len(selectedCases), sum(map(lambda c: testCompl[c], selectedCases)), selectedCases)


def makeHtmlTable(coverage, solutions, testCases):
    """Generate the table for coverage of solutions by testCases."""
    solCovs = []
    solOk = []
    for solution in solutions:
        solCovs.append(coverage.get(solution['name'], {}))
        solOk.append(False)

    # Generate lines for each test
    innerHtml = ''
    for case in testCases:
        covOk = False
        line = ''
        for i, cov in enumerate(solCovs):
            if case not in cov:
                line += '<td class="coverageNoTest">not tested</td>'
            elif cov[case] == 'success':
                line += '<td>success</td>'
            else:
                line += '<td class="coverageOk">%s</td>' % cov[case]
                covOk = True
                solOk[i] = True
        if covOk:
            innerHtml += '<tr><td class="testOk">%s</td>' % case
        else:
            innerHtml += '<tr><td class="testNok">%s</td>' % case
        innerHtml += line
        innerHtml += '</tr>'

    # Generate colored table headers
    html = '<table class="coverageTable">'
    html += '<tr><th class="corner"></th>'
    for i, solution in enumerate(solutions):
        if solOk[i]:
            html += '<th class="solCovered">%s</th>' % solution['name']
        else:
            html += '<th class="solNotCovered">%s</th>' % solution['name']
    html += '</tr>'

    html += innerHtml
    html += '</table>'

    return html

def genHtml(args):
    """Generate the coverage HTML table."""
    data = loadData(args)

    html = """<!DOCTYPE html>
<html><head>
<style type="text/css">
.coverageTable {
    background-color: #CCCCCC;
    border: 1px;
}

th.corner {
    border-bottom: 2px solid;
    border-right: 2px solid;
}

th.solCovered {
    border-bottom: 2px solid;
    background-color: #33FF33;
}

th.solNotCovered {
    border-bottom: 2px solid;
    background-color: #FF3333;
}

td.testOk {
    border-right: 2px solid;
    background-color: #33FF33;
    font-weight: bold;
}

td.testNok {
    border-right: 2px solid;
    background-color: #FF3333;
    font-weight: bold;
}

td.coverageOk {
    background-color: #66FF66;
}

td.coverageNoTest {
    background-color: #FF6666;
}
</style>
</head>
<body>
<h2>Coverage tables</h2>
<p>This table shows the coverage: which tests find errors in which solutions.</p>
<p>Green indicates a solution/test/pair covered (which means that an error has been found). Red indicates a solution which isn't covered, or a test which covers nothing.</p>
<hr />
<h3>Selected cases</h3>
<p>These are the selected cases which will be exported for usage with the task when running <i>testSelect.py export</i>.</p>
<p>These cases are automatically selected by <i>testSelect.py select</i>; you can manually change the selection by editing the file <i>testSelect.json</i> in the task folder, and adding/removing test case names in the key <i>"selected"</i>.</p>
"""

    # Selected cases table
    if len(data.get('selected', [])) > 0:
        html += makeHtmlTable(data['coverage'], data['solutions'], data['selected'])
    else:
        html += '<p>No test cases selected yet.</p>'

    # All test cases table
    html += """<hr />
<h3>All test cases</h3>"""

    html += makeHtmlTable(data['coverage'], data['solutions'], map(lambda c: c['name'], data['testCases']))
    html += '</body></html>'

    return html

def askQuestionBool(prompt):
    """Ask a question, return a boolean corresponding to the answer."""
    answer = input("%s [y/N] " % prompt)
    return (answer.lower() in ['y', 'yes'])

def globOfGlobs(folder, globlist):
    """Makes the combined list of files corresponding to a list of globs in a
    folder."""
    filelist = []
    for g in globlist:
        # We sort file list for each glob, but keep the original glob order, so
        # that ['test*.in', 'mytest.in'] will give a predictable
        # ['test1.in', 'test2.in', 'mytest.in']
        curglob = glob.glob(os.path.join(folder, g))
        curglob.sort()
        for f in curglob:
            if f not in filelist:
                filelist.append(f)
    return filelist


### Actions
def addsol(args):
    """Manually add a solution to the pool of solutions."""
    data = loadData(args)

    paths = []
    for path in args.path:
        if os.path.isfile(path):
            paths.append(path)
        elif os.path.isdir(path):
            if args.recursive:
                for root, dirs, files in os.walk(path):
                    for f in files:
                        paths.append(os.path.join(root, f))
            else:
                print("Path '%s' is a folder, use '-r' option to add files in it." % path)

    for path in paths:
        solName = os.path.basename(path)

        if len(list(filter(lambda s: s['name'] == solName, data['solutions']))) > 0:
            print("Solution with the name '%s' already registered." % solName)
            continue

        print("Adding solution '%s'..." % solName)
        newSol = {
            'name': solName,
            'language': args.lang,
            'path': os.path.relpath(path, args.taskpath)}
        data['solutions'].append(newSol)

    saveData(args, data)
    return 0


def addtest(args):
    """Manually add a test case to the pool of solutions."""
    data = loadData(args)

    paths = []
    for path in args.path:
        if os.path.isfile(path):
            paths.append(path)
        elif os.path.isdir(path):
            if args.recursive:
                for root, dirs, files in os.walk(path):
                    for f in files:
                        paths.append(os.path.join(root, f))
            else:
                print("Path '%s' is a folder, use '-r' option to add files in it." % path)

    for path in paths:
        caseName = os.path.basename(path)

        if len(list(filter(lambda t: t['name'] == caseName, data['testCases']))) > 0:
            print("Test case with the name '%s' already registered." % caseName)
            continue

        print("Adding test case '%s'..." % caseName)
        newCase = {
            'name': caseName,
            'path': os.path.relpath(path, args.taskpath)}
        data['testCases'].append(newCase)

    saveData(args, data)
    return 0


def compute(args):
    """Check which test cases find which errors in which test cases."""
    data = loadData(args)

    for solution in data['solutions']:
        if solution['name'] not in data['coverage']:
            data['coverage'][solution['name']] = {}

        # Only execute tests which haven't been tested yet
        solCov = data['coverage'][solution['name']]
        casesToTest = {}
        for case in data['testCases']:
            if case.get('enabled', True) and (case['name'] not in solCov):
                casesToTest[case['name']] = case
        if len(casesToTest) == 0:
            continue

        # Execute taskgrader
        print("Testing %d cases with solution %s..." % (len(casesToTest), solution['name']))
        evaluationJson = makeEvaluationJson(args.taskpath, solution, casesToTest)
        proc = subprocess.Popen([CFG_TASKGRADER], stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
        procOut, procErr = proc.communicate(input=json.dumps(evaluationJson))

        # Handle some errors
        if proc.returncode > 0:
            print("Error: Taskgrader exited with return code %d, output:" % proc.returncode)
            print(procOut)
            print(procErr)
            print("Ignoring results.")
            continue

        try:
            resultJson = json.loads(procOut)
        except:
            print("Error: Taskgrader returned invalid JSON data, output:")
            print(procOut)
            print(procErr)
            print("Ignoring results.")
            continue

        # Read test reports
        # Note : the modification of these variables will modify the variable
        # 'data' (as they are pointers to values inside 'data')
        for report in resultJson['executions'][0]['testsReports']:
            testName = report['name']
            if testName[:3] != 'ts-':
                print("Warning: ignoring test %s, wasn't sent by testSelect." % testName)
                continue
            testName = "%s.in" % testName[3:]
            case = casesToTest[testName]
            if report['sanitizer']['exitCode'] != 0:
                print("Test %s was not validated by sanitizer, disabling usage..." % testName)
                case['enabled'] = False
                continue
            elif report['execution']['exitCode'] != 0:
                if report['execution']['wasKilled']:
                    solCov[testName] = 'timeout'
                else:
                    solCov[testName] = 'error'
            elif report['checker']['stdout']['data'].split()[0] == '100':
                solCov[testName] = 'success'
            else:
                solCov[testName] = 'badgrade'

    saveData(args, data)


def select(args):
    """Find the smallest subset of test cases finding errors in each solution."""
    data = loadData(args)
    if len(data['solutions']) == 0:
        print("Error: no solutions defined.")
        return 1

    if len(data['testCases']) == 0:
        print("Error: no test cases defined.")
        return 1

    solutions = []
    testCases = []
    testCov = {}
    testCompl = {}
    covMissing = 0

    # Check coverage for each solution
    # testCases will contain only cases which cover at least one solution
    for sol in data['solutions']:
        if sol['name'] not in data['coverage']:
            print("Warning: No coverage data for solution '%s'. Ignoring this solution." % sol['name'])
            continue

        solCov = data['coverage'][sol['name']]
        solCovered = False
        for case in data['testCases']:
            if case['name'] not in solCov:
                covMissing += 1
            elif solCov[case['name']] != 'success':
                solCovered = True
                if case['name'] in testCov:
                    testCov[case['name']].add(sol['name'])
                else:
                    # Add test case to the pool of possible selections
                    testCov[case['name']] = set([sol['name']])
                    testCases.append(case['name'])
                    testCompl[case['name']] = testComplexity(case, args.taskpath)

        if solCovered:
            solutions.append(sol['name'])
        else:
            print("Warning: Solution '%s' not covered. Ignoring this solution." % sol['name'])

    if covMissing > 0:
        print("Warning: coverage data missing for %d solution/test case pair(s)." % covMissing)

    # Find the smallest cover
    number, totalCompl, selected = greedyCover(testCases, testCov, testCompl, set(solutions))

    print("Best selection found for %d solutions: %d tests, complexity %d." % (len(solutions), number, totalCompl))
    selected.sort()
    data['selected'] = selected

    saveData(args, data)


def html(args):
    """Output an HTML document with the test coverage."""
    print(genHtml(args))
    return 0


def serve(args):
    """Serve the HTML document with the test coverage."""
    # Use bottle module for serving
    import bottle

    @bottle.route('/')
    def index():
        return genHtml(args)

    bottle.run(host='localhost', port=8000)
    return 0


def export(args):
    """Export selected test cases for usage by the task."""
    data = loadData(args)

    # Warn about a few errors
    tsPath = os.path.join(args.taskpath, 'taskSettings.json')

    warning = False
    if not os.path.isfile(tsPath):
        print("Warning: no 'taskSettings.json' file in current folder.")
        taskSettings = {}
    else:
        taskSettings = json.load(open(tsPath, 'r'))

    testsPath = os.path.join(args.taskpath, 'tests/files/')
    try:
        testsList = list(filter(lambda x: x[-3:] == '.in', os.listdir(testsPath)))
    except:
        testsList = []
    if len(testsList) > 0:
        print("Warning: test cases found in 'tests/files/'.")
        print("You can use 'testSelect.py cleanup' to clean up old test cases from this task.")
        if not askQuestionBool("Do you still want to continue?"):
            print("Aborting.")
            return 1

    # Make test case dir
    try:
        os.makedirs(testsPath)
    except:
        pass

    # Save new test cases
    filterTests = []
    for case in data['testCases']:
        if case['name'] in data['selected']:
            caseName = case['name']
            if caseName[-3:] != '.in':
                caseName += '.in'
            filterTests.append(caseName)
            targetPath = os.path.join(testsPath, caseName)

            if case.get('path', None):
                casePath = os.path.join(args.taskpath, case['path'])
                # We're saving a test case to the same path
                if casePath == targetPath:
                    continue 
                testData = open(os.path.join(args.taskpath, case['path']), 'r').read()
            else:
                testData = case['content']
            open(targetPath, 'w').write(testData)

    taskSettings['defaultFilterTests'] = filterTests
    json.dump(taskSettings, open(tsPath, 'w'))

    return 0


def cleanup(args):
    """Clean up old test cases."""
    tsPath = os.path.join(args.taskpath, 'taskSettings.json')
    if not os.path.isfile(tsPath):
        print("Error: no 'taskSettings.json' file in current folder.")
        return 1
    taskSettings = json.load(open(tsPath, 'r'))
    if 'defaultFilterTests' not in taskSettings:
        print("Error: no specific tests configured for this task.")
        return 1

    # List test cases
    testsPath = os.path.join(args.taskpath, 'tests/files/')
    allCases = os.listdir(testsPath)
    curCases = list(map(lambda p: os.path.relpath(p, testsPath), globOfGlobs(testsPath, taskSettings['defaultFilterTests'])))
    oldCases = list(filter(lambda c: c not in curCases, allCases))

    if len(oldCases) == 0:
        print("No old tests to move/remove.")
        return 0

    print("%d old tests found." % len(oldCases))
    if args.delete:
        print("Deleting them...")
        for c in oldCases:
            os.remove(os.path.join(testsPath, c))
    else:
        print("Moving them to 'tests/oldcases/'...")
        oldcPath = os.path.join(args.taskpath, 'tests/oldcases/')
        try:
            os.makedirs(oldcPath)
        except:
            pass
        for c in oldCases:
            shutil.move(os.path.join(testsPath, c), oldcPath)

    return 0



if __name__ == '__main__':
    # Parse command-line arguments
    argParser = argparse.ArgumentParser(description="""This tool finds a subset
        of test cases which are sufficient to find errors in solutions.""")

    # Parsers for each sub-command
    subparsers = argParser.add_subparsers(help='Action', dest='action')

    helpParser = subparsers.add_parser('help', help='Get help on an action')
    helpParser.add_argument('helpaction', help='Action to get help for', nargs='?', metavar='action')

    addsolParser = subparsers.add_parser('addsol', help='Manually add a solution', description="""
        Manually add a solution to the pool of available solutions.""")
    addsolParser.add_argument('-l', '--lang', help='Solution language', required=True)
    addsolParser.add_argument('-r', '--recursive', help='Add all solutions from folders', action='store_true')
    addsolParser.add_argument('-t', '--taskpath', help='Task path', default='.')
    addsolParser.add_argument('path', help='Paths of solutions to add', nargs='+')

    addtestParser = subparsers.add_parser('addtest', help='Manually add a test case', description="""
        Manually add a test case to the pool of available test cases.""")
    addtestParser.add_argument('-r', '--recursive', help='Add all tests from folders', action='store_true')
    addtestParser.add_argument('-t', '--taskpath', help='Task path', default='.')
    addtestParser.add_argument('path', help='Paths of test cases to add', nargs='+')

    cleanupParser = subparsers.add_parser('cleanup', help='Clean up old test cases', description="""
        Move or remove old test cases.""")
    cleanupParser.add_argument('-d', '--delete', help='Delete instead of moving', action='store_true')
    cleanupParser.add_argument('-t', '--taskpath', help='Task path', default='.')

    computeParser = subparsers.add_parser('compute', help='Check solutions against test cases', description="""
        Check all solutions against all test cases from the pool (except if
        already checked).""")
    computeParser.add_argument('-t', '--taskpath', help='Task path', default='.')

    exportParser = subparsers.add_parser('export', help='Export selected test cases into the task', description="""
        Save the selected test cases for usage by the task.""")        
    exportParser.add_argument('-f', '--force', help='Force export', action='store_true')
    exportParser.add_argument('-t', '--taskpath', help='Task path', default='.')

    htmlParser = subparsers.add_parser('html', help='Outputs an HTML table about test coverage', description="""
        Outputs an HTML table describing which tests find errors in which
        solutions.""")
    htmlParser.add_argument('-t', '--taskpath', help='Task path', default='.')

    selectParser = subparsers.add_parser('select', help='Select the best test cases', description="""
        Find the smallest number of test cases necessary to cover all solution
        errors.""")
    selectParser.add_argument('-t', '--taskpath', help='Task path', default='.')

    serveParser = subparsers.add_parser('serve', help='Serve an HTML table about test coverage', description="""
        Serves an HTML table describing which tests find errors in which
        solutions.""")
    serveParser.add_argument('-t', '--taskpath', help='Task path', default='.')

    args = argParser.parse_args()

    # List of parsers and functions handling each action
    ACTIONS = {
        'addsol': {'p': addsolParser, 'f': addsol},
        'addtest': {'p': addtestParser, 'f': addtest},
        'cleanup': {'p': cleanupParser, 'f': cleanup},
        'compute': {'p': computeParser, 'f': compute},
        'export': {'p': exportParser, 'f': export},
        'html': {'p': htmlParser, 'f': html},
        'select': {'p': selectParser, 'f': select},
        'serve': {'p': serveParser, 'f': serve}
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
