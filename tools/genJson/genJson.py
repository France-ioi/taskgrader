#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT


import argparse, fnmatch, glob, json, os, re, shutil, sys, subprocess, tempfile, time
from config import *

# genJson folder
SELFDIR = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
# genJson version (grabbed from git log)
VERSION = ''

def getFileList(path):
    """Makes a list of sub-paths of files found in path."""
    l = []
    for x in os.listdir(path):
        if x in CFG_IGNORE_PATHS:
            continue
        elif os.path.isfile(os.path.join(path, x)):
            l.append(x)
        elif os.path.isdir(os.path.join(path, x)):
            l.extend(map(lambda a: os.path.join(x, a), getFileList(os.path.join(path, x))))
    return l


def isIgnored(path, ignoreList):
    """Checks a filename against a list of ignored patterns."""
    for pattern in ignoreList:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


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


def getScript(path):
    """Return the fileDescr of a default script packaged with genJson."""
    # Default scripts are in the `script` subfolder
    # We put the script's content directly into the JSON
    f = open(os.path.join(SELFDIR, 'scripts', path), 'rb')
    return {'name': os.path.basename(path),
            'content': f.read().decode('utf-8')}


def getTaskFile(path):
    """Return the fileDescr of a file in the task.
    path must be the relative path to the task."""
    return {'name': os.path.basename(path),
            'path': os.path.join('$TASK_PATH', path)}


def genDefaultParams(taskPath, taskSettings):
    """Generates the defaultParams.json for a path pointing to a task."""

    # defaultParams from config.py
    defaultParams = {
        'rootPath': CFG_ROOTDIR,
        'defaultToolCompParams': CFG_DEF_TOOLCOMPPARAMS,
        'defaultToolExecParams': CFG_DEF_TOOLEXECPARAMS,
        }

    # Add genJson version (allows to check if it was generated with the latest
    # version)
    defaultParams['genJsonVersion'] = VERSION

    # Tests and libraries given as is
    defExtraTests = []

    defFilterTests = ['*.in']
    defFilterTestsPy = '@defaultFilterTests'

    defDependencies = {}
    for lang in CFG_LANGUAGES:
        defDependencies[lang] = []


    devnull = open(os.devnull, 'w')

    ### Generator(s)
    if taskSettings.has_key('generator') and os.path.isfile(os.path.join(taskPath, taskSettings['generator'])):
        print 'Generator detected'
        # We use a wrapper for the taskgrader to fetch all the files properly
        defGenerator = {'id': 'defaultGenerator',
            'compilationDescr': {'language': 'sh',
                'files': [getScript('wrapGen.sh')],
                'dependencies': []},
            'compilationExecution': '@defaultToolCompParams'}

        # Auto-detect generator dependencies
        (genDir, genFilename) = os.path.split(os.path.join(taskPath, taskSettings['generator']))

        genDependencies = []
        genDepPaths = {}

        # Make a list of basename of all files in the generator folder
        # If we detect 'generator' in one of the files, we'll add all files
        # named 'generator.*' as dependencies
        for f in getFileList(genDir):
            (filename, ext) = os.path.splitext(os.path.basename(f))
            if genDepPaths.has_key(filename):
                genDepPaths[filename].append(f)
            else:
                genDepPaths[filename] = [f]

        genFileNoExt = os.path.splitext(genFilename)[0]

        genPossibleDeps = genDepPaths.keys()
        genPossibleDeps.remove(genFileNoExt)
        genNewDeps = [genFileNoExt]
        genAllDeps = [genFileNoExt]
        while genNewDeps != []:
            # We check the new dependencies for their own dependencies
            genCurDeps = []
            for x in genNewDeps:
                genCurDeps.extend(genDepPaths[x])
            genNewDeps = []
            for d in genCurDeps:
                data = open(os.path.join(taskPath, genDir, d), 'r').read() # Memory-inefficient
                for possdep in genPossibleDeps[:]:
                    if re.search('\W%s\W' % possdep.replace('.', '\\.'), data):
                        # This dependency is probably needed
                        genAllDeps.append(possdep)
                        genNewDeps.append(possdep)
                        genPossibleDeps.remove(possdep)

        # Add each dependency
        for possdep in genAllDeps:
            genDependencies.extend(map(
                    lambda p: {'name': p,
                               'path': os.path.join('$TASK_PATH', genDir, p)},
                    genDepPaths[possdep]))

        # Add dependencies given in taskSettings
        genDependencies.extend(taskSettings.get('generatorDeps', []))

        # Extra dependencies to check for and add
        extraGenDeps = globOfGlobs(taskPath, CFG_GEN_EXTRADEPS)
        for f in extraGenDeps:
            genDependencies.append(getTaskFile(f))
        defGenerator['compilationDescr']['dependencies'] = genDependencies
        print "Dependencies found for generator: " + ', '.join(map(lambda x: x['name'], genDependencies))

        # Generations
        defGeneration = {'id': 'defaultGeneration',
                    'idGenerator': 'defaultGenerator',
                    'genExecution': '@defaultToolExecParams'}

        # We execute the generator to know which files it generates
        tmpDir = tempfile.mkdtemp()
        os.mkdir(os.path.join(tmpDir, 'gen'))
        for dep in genDependencies:
            path = dep['path'].replace('$TASK_PATH', taskPath).replace('$ROOT_PATH', CFG_ROOTDIR)
            shutil.copy(path, os.path.join(tmpDir, 'gen', dep['name']))
        proc = subprocess.Popen(['/bin/sh', os.path.join(tmpDir, 'gen', genFilename)], cwd=tmpDir + '/gen/', stdout=devnull, stderr=devnull)
        for i in range(CFG_EXEC_TIMEOUT): # Timeout after 60 seconds
            if not (proc.poll() is None):
                break
            time.sleep(1)
        if not (proc.poll() is None):
            # The generator terminated
            if proc.poll() > 0:
                print 'Warning: generator exited with non-zero exit code %d' % proc.poll()

            if os.path.isdir(tmpDir + '/files/all/') and os.path.isdir(tmpDir + '/files/python/'):
                # We have specific tests for Python
                defFilterTests = ['all-*.in']
                defFilterTestsPy = ['py-*.in']

            # Auto-detect generated dependencies
            for f in glob.glob(tmpDir + '/files/lib/*/*'):
                lang = f.split('/')[-2]
                defDependencies[lang].append({'name': os.path.basename(f)})
            for f in glob.glob(tmpDir + '/files/run/*'):
                defDependencies['python'].append({'name': os.path.basename(f)})

            shutil.rmtree(tmpDir)
        else:
            # We got a timeout while executing the generator
            proc.kill()
            raise Exception("Generator didn't end in %d seconds (change CFG_EXEC_TIMEOUT if required).\nGeneration was taking place in `%s`." % (CFG_EXEC_TIMEOUT, tmpDir))

    else:
        # No generator detected, the files are (normally) provided directly
        print 'No generator detected'
        defGenerator = None
        defGeneration = None


    # Detect files given directly without generator
    if taskSettings.has_key('extraDir') and os.path.isdir(os.path.join(taskPath, taskSettings['extraDir'])):
        print 'Extra files detected'
        extraDir = os.path.join(taskPath, taskSettings['extraDir'])
        # Extra tests
        if os.path.isdir(os.path.join(extraDir, 'all/')) and os.path.isdir(os.path.join(extraDir, 'python/')):
            # We have specific tests for python
            for f in globOfGlobs(extraDir, ['all/*.in', 'all/*.out']):
                if not isIgnored(os.path.basename(f), taskSettings.get('ignoreTests', [])):
                    defExtraTests.append({'name': 'all-' + os.path.basename(f),
                                          'path': os.path.join('$TASK_PATH', os.path.relpath(f, taskPath))})
            for f in globOfGlobs(taskPath, ['files/*.in', 'files/*.out']):
                if not isIgnored(os.path.basename(f), taskSettings.get('ignoreTests', [])):
                    defExtraTests.append({'name': 'py-' + os.path.basename(f),
                                          'path': '$TASK_PATH/' + os.path.relpath(f, taskPath)})
            defFilterTests = ['all-*.in']
            defFilterTestsPy = ['py-*.in']
        else:
            # Tests are the same for all languages
            for f in globOfGlobs(extraDir, ['*.in', '*.out']):
                if not isIgnored(os.path.basename(f), taskSettings.get('ignoreTests', [])):
                    defExtraTests.append(getTaskFile(os.path.relpath(f, taskPath)))

        # Auto-detected dependencies
        for f in glob.glob(os.path.join(extraDir, 'lib/*/*')):
            lang = CFG_LANGUAGES_OLD_NEW[f.split('/')[-2]]
            defDependencies[lang].append(getTaskFile(os.path.relpath(f, taskPath)))
        for f in glob.glob(os.path.join(extraDir, 'run/*')):
            defDependencies['python'].append(getTaskFile(os.path.relpath(f, taskPath)))

    # Update default params
    defaultParams.update({'defaultGenerator': defGenerator,
                          'defaultGeneration': defGeneration,
                          'defaultExtraTests': defExtraTests})
    # Filter tests content
    defaultParams['defaultFilterTests'] = defFilterTests
    for lang in CFG_LANGUAGES:
        if lang == 'python':
            defaultParams['defaultFilterTests-python'] = defFilterTestsPy
        else:
            defaultParams['defaultFilterTests-' + lang] = '@defaultFilterTests'

    # Dependencies auto-detected (not necessarily reliable)
    # If no dependencies were detected for cpp, we use the c dependencies
    if defDependencies['cpp'] == []:
        defDependencies['cpp'] = '@defaultDependencies-c'
    for lang in CFG_LANGUAGES:
        defaultParams['defaultDependencies-' + lang] = defDependencies[lang]

    # Aliases for python2 and python3
    defaultParams['defaultFilterTests-python2'] = '@defaultFilterTests-python'
    defaultParams['defaultFilterTests-python3'] = '@defaultFilterTests-python'
    defaultParams['defaultDependencies-python2'] = '@defaultDependencies-python'
    defaultParams['defaultDependencies-python3'] = '@defaultDependencies-python'

    # Add dependencies and filterTest aliases for old languages
    for lang in CFG_LANGUAGES_OLD_NEW.keys():
        newlang = CFG_LANGUAGES_OLD_NEW[lang]
        if newlang != lang and lang not in CFG_LANGUAGES:
            defaultParams['defaultDependencies-' + lang] = '@defaultDependencies-' + newlang
            defaultParams['defaultFilterTests-' + lang] = '@defaultFilterTests-' + newlang

    ### Sanitizer
    if taskSettings.has_key('sanitizer') and os.path.isfile(os.path.join(taskPath, taskSettings['sanitizer'])):
        print 'Sanitizer detected'

        # Find sanitizer language
        (r, ext) = os.path.splitext(taskSettings['sanitizer'])
        if taskSettings.has_key('sanitizerLang'):
            sLang = taskSettings['sanitizerLang']
        elif CFG_LANGEXTS.has_key(ext):
            sLang = CFG_LANGEXTS[ext]
        else:
            raise Exception("Couldn't auto-detect language for `%s`.\nAdd language to taskSettings, key 'sanitizerLang', to specify language." % taskSettings['sanitizer'])

        if sLang == 'cpp':
            # We test whether the sanitizer is C++11 or C++
            tmpDir = tempfile.mkdtemp()
            sanFilename = os.path.basename(taskSettings['sanitizer'])
            shutil.copy(os.path.join(taskPath, taskSettings['sanitizer']), os.path.join(tmpDir, sanFilename))
            for dep in taskSettings.get('sanitizerDeps', []):
                path = dep['path'].replace('$TASK_PATH', taskPath).replace('$ROOT_PATH', CFG_ROOTDIR)
                shutil.copy(path, os.path.join(tmpDir, dep['name']))
                try:
                    shutil.copy(f, tmpDir)
                except:
                    pass
            proc = subprocess.Popen(['/usr/bin/g++', '-std=gnu++11', os.path.join(tmpDir, sanFilename)],
                    cwd=tmpDir, stdout=devnull, stderr=devnull)
            for i in range(60): # Timeout after 60 seconds
                if not (proc.poll() is None):
                    break
                time.sleep(1)
            if proc.poll() == 0:
                print 'C++11 sanitizer detected'
                sLang = 'cpp11'
            else:
                # We default to C++ (non-11)
                sLang = 'cpp'
                try:
                    proc.kill()
                except:
                    pass
            shutil.rmtree(tmpDir)

        defSanitizer = {
                'compilationDescr': {'language': sLang,
                    'files': [getTaskFile(taskSettings['sanitizer'])],
                    'dependencies': taskSettings.get('sanitizerDeps', [])},
                'compilationExecution': '@defaultToolCompParams',
                'runExecution': '@defaultToolExecParams'}
        if os.path.isfile(os.path.join(taskPath, 'gen/constants.h')): # TODO
            defSanitizer['compilationDescr']['dependencies'].append({
                    'name': 'constants.h',
                    'path': '$TASK_PATH/tests/gen/constants.h'})
    else:
        print 'No sanitizer detected'
        # No sanitizer, we use /bin/true as a 'sanitizer'
        defSanitizer = {
                'compilationDescr': {'language': 'sh',
                                    'files': [getScript('true.sh')],
                                    'dependencies': []},
                'compilationExecution': '@defaultToolCompParams',
                'runExecution': '@defaultToolExecParams'}

    defaultParams['defaultSanitizer'] = defSanitizer


    ### Checker
    if taskSettings.has_key('checker') and os.path.isfile(os.path.join(taskPath, taskSettings['checker'])):
        print 'Checker detected'
        # A checker is given

        # Find checker language
        (r, ext) = os.path.splitext(taskSettings['checker'])
        if taskSettings.has_key('checkerLang'):
            cLang = taskSettings['checkerLang']
        elif CFG_LANGEXTS.has_key(ext):
            cLang = CFG_LANGEXTS[ext]
        else:
            raise Exception("Couldn't auto-detect language for `%s`.\nAdd language to taskSettings, key 'checkerLang', to specify language." % taskSettings['checker'])

        defChecker = {
            'compilationDescr': {'language': cLang,
                'files': [getTaskFile(taskSettings['checker'])],
                'dependencies': taskSettings.get('checkerDeps', [])},
            'compilationExecution': '@defaultToolCompParams',
            'runExecution': '@defaultToolExecParams'}
    else:
        print 'No checker detected, using defaultChecker.sh'
        # We use a generic checker (a wrapper around diff)
        defChecker = {
            'compilationDescr': {'language': 'sh',
                'files': [getScript('defaultChecker.sh')],
                'dependencies': []},
            'compilationExecution': '@defaultToolCompParams',
            'runExecution': '@defaultToolExecParams'}

    defaultParams['defaultChecker'] = defChecker


    ### Default evaluation keys
    defaultParams.update({
        'defaultEvaluationGenerators': ['@defaultGenerator'],
        'defaultEvaluationGenerations': ['@defaultGeneration'],
        'defaultEvaluationExtraTests': '@defaultExtraTests',
        'defaultEvaluationSanitizer': '@defaultSanitizer',
        'defaultEvaluationChecker': '@defaultChecker',
        'defaultEvaluationSolutions': [{
            'id': '@solutionId',
            'compilationDescr': {
                'language': '@solutionLanguage',
                'files': [{'name': '@solutionFilename',
                           'path': '@solutionPath',
                           'content': '@solutionContent'}],
                'dependencies': '@solutionDependencies'
                },
            'compilationExecution': '@defaultSolutionCompParams'
            }],
        'defaultEvaluationExecutions': [{
            'id': '@solutionExecId',
            'idSolution': '@solutionId',
            'filterTests': '@solutionFilterTests',
            'runExecution': '@defaultSolutionExecParams'
            }],

        'defaultSolutionCompParams': CFG_TESTSOLPARAMS,
        'defaultSolutionExecParams': CFG_TESTSOLPARAMS,

        # Default values if not specified
        'solutionDependencies': [],
        'solutionFilterTests': '@defaultFilterTests',
        'solutionId': 'solution',
        'solutionExecId': 'execution',
        # Add empty solutionPath and solutionContent. If a path is specified,
        # it will be used; else if a content is specified, it's the one which
        # will be used. These two keys just allow preprocessJson from
        # taskgrader.py to work without raising an error.
        'solutionPath': '',
        'solutionContent': ''
        })


    ### Handle defaults in the taskSettings and overrideParams
    for k in taskSettings.keys():
        if k[:7] == 'default':
            # Copy all 'default' keys from taskSettings
            defaultParams[k] = taskSettings[k]

    defaultParams.update(taskSettings.get('overrideParams', {}))


    return defaultParams


def processPath(path, args):
    """Process a task path, generating defaultParams for it and performing an
    auto-test with the taskgrader."""

    print '*** Generating defaultParams for ' + path
    # Settings for the task
    taskSettings = {}
    taskSettings.update(CFG_DEF_TASKSETTINGS)
    try:
        taskSettings.update(json.load(open(os.path.join(path, 'taskSettings.json'), 'r')))
    except:
        pass

    # Generate and save defaultParams
    defaultParams = genDefaultParams(path, taskSettings)
    json.dump(defaultParams, open(os.path.join(path, 'defaultParams.json'), 'w'))
    print ''
    if args.verbose:
        print 'Generated defaultParams:'
        print json.dumps(defaultParams)
        print ''

    taskPath = os.path.relpath(path, CFG_ROOTDIR)

    # Make test evaluation
    correctSolutions = taskSettings.get('correctSolutions', [])
    if len(taskSettings.get('correctSolutions', [])) > 0:
        print '* Auto-test with correctSolutions'

        # Error on any correctSolution
        cError = False
        # max number of test cases tested for a single correctSolution
        maxNbTotal = 0
        # correctSolutions which compiled
        nbCsOk = 0
        # total number of test cases, sanitizer validated test cases, and
        # checker executions
        nbTests, nbSan, nbSol, nbCheck = 0, 0, 0, 0

        # Do an evaluation for each correctSolution
        for cs in correctSolutions:
            curError = False

            # Call stdGrade to generate the evaluation
            csPath = os.path.join(cs['path'].replace('$TASK_PATH', path))
            cmd = [os.path.join(SELFDIR, '../stdGrade/genStdTaskJson.py'),
                '-p', path]
            if cs.has_key('language'):
                cmd.extend(['-l', cs['language']])
            cmd.append(csPath)
            genStd = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (genStdOut, genStdErr) = genStd.communicate()

            if args.verbose:
                print ''
                print 'Generated test evaluation for correctSolution %s:' % csPath
                print genStdOut
                print ''
            try:
                testEvaluation = json.loads(genStdOut)
            except:
                print "Error: couldn't generate test evaluation for correctSolution `%s`." % csPath
                continue

            proc = subprocess.Popen([CFG_TASKGRADER], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            (procOut, procErr) = proc.communicate(json.dumps(testEvaluation))
            if args.verbose:
                print ''
                print 'Test evaluation report:'
                print procOut
                print ''

            # Read output JSON
            try:
                outJson = json.loads(procOut)
            except:
                print "/!\ Fatal error: received non-JSON data."
                cError = True
                continue

            try:
                execution = outJson['executions'][0]
            except:
                print "/!\ Compilation failed for correctSolution `%s`." % csPath
                cError = True
                continue

            nbCsOk += 1

            # Totals
            nbTests += len(execution['testsReports'])
            for report in execution['testsReports']:
                if report['sanitizer']['exitCode'] == 0:
                    nbSan += 1
                    if report['execution']['exitCode'] == 0:
                        nbSol += 1
                        if report['checker']['exitCode'] == 0:
                            nbCheck += 1

            nbOk = 0
            nbTotal = len(execution['testsReports'])
            maxNbTotal = max(maxNbTotal, nbTotal)
            # Check grade for each test
            for test in execution['testsReports']:
                testGrade = None
                try:
                    testGrade = int(test['checker']['stdout']['data'].split()[0])
                except:
                    if test.has_key('execution'):
                        if test['execution']['exitCode'] == 0:
                            print "Checker error, output:\n%s%s" % (test['checker']['stdout']['data'], test['checker']['stderr']['data'])
                        else:
                            print "Solution exited with non-zero exit code:\n%s%s" % (test['execution']['stdout']['data'], test['execution']['stderr']['data'])
                    elif test['sanitizer']['exitCode'] > 0:
                        print "Sanitizer didn't validate test case:\n%s%s" % (test['sanitizer']['stdout']['data'], test['sanitizer']['stderr']['data'])
                    else:
                        print "Error reading test data."
                    curError = True
                if testGrade == cs['grade']:
                    nbOk += 1
                elif testGrade is not None:
                    print "Got grade %d instead of %d" % (testGrade, cs['grade'])
                    curError = True
            if nbOk != nbTotal:
                print "/!\ Test failed on %s: %d/%d grades incorrect" % (cs['path'], nbTotal-nbOk, nbTotal)
                curError = True
            if nbTotal != cs.get('nbtests', nbTotal):
                print "/!\ Test failed on %s: %d tests done / %d tests expected" % (cs['path'], nbTotal, cs['nbtests'])
                curError = True

            if curError:
                cError = True
            else:
                print "Test successful on correctSolution `%s`." % cs['path']

        print ""
        print "Totals: %d tests, %d test cases validated by sanitizer," % (nbTests, nbSan)
        print "%d successful solution executions, %d successful checker executions." % (nbSol, nbCheck)
        if nbSan < nbTests:
            print '/!\ %d test cases not validated by sanitizer' % (nbTests - nbSan)
            cError = True
        if nbCheck < nbSan:
            print '/!\ Checker failed on %d tests' % (nbSan - nbCheck)
            cError = True

        if cError:
            tasksWithErrors.append(path)
        else:
            print "Test successful on %d correctSolutions with up to %d test cases." % (len(taskSettings['correctSolutions']), maxNbTotal)

    else:
        # No correctSolutions, we use a dummy solution (true.sh)
        testEvaluation = {
            'rootPath': CFG_ROOTDIR,
            'taskPath': '$ROOT_PATH/%s' % taskPath,
            'extraParams': {
                'solutionLanguage': 'shell',
                'solutionFilename': 'true.sh',
                'solutionPath': os.path.join(SELFDIR, 'scripts', 'true.sh'),
                'solutionDependencies': []
                }
            }

        if args.verbose:
            print 'Generated test evaluation with a dummy solution:'
            print json.dumps(testEvaluation)
            print ''

        print '* Auto-test with a dummy solution'
        proc = subprocess.Popen([CFG_TASKGRADER], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        (procOut, procErr) = proc.communicate(json.dumps(testEvaluation))
        if args.verbose:
            print ''
            print 'Test evaluation report:'
            print procOut
            print ''

        # Read output JSON
        try:
            outJson = json.loads(procOut)
        except:
            print '/!\ Fatal error: received non-JSON data.'
            return 1

        print '* Results of the test with a dummy solution'
        print ''
        print "/!\ Please use a correctSolution for an actual test; these results aren't"
        print "accurate and may not indicate any actual success or failure of the test."
        print ''
        try:
            execution = outJson['executions'][0]
        except:
            return 2
        nbTests = len(execution['testsReports'])
        nbSan, nbSol, nbCheck = 0, 0, 0
        for report in execution['testsReports']:
            if report['sanitizer']['exitCode'] == 0:
                nbSan += 1
                if report['execution']['exitCode'] == 0:
                    nbSol += 1
                    if report['checker']['exitCode'] == 0:
                        nbCheck += 1
        print "Test with a dummy solution: %d test cases," % nbTests
        print "%d cases validated by sanitizer, %d successful dummy solution executions," % (nbSan, nbSol)
        print "%d successful checker executions." % nbCheck
        if nbSan < nbTests:
            print '%d test cases not validated by sanitizer' % (nbTests - nbSan)
        if nbCheck < nbSol:
            print 'Checker failed on %d tests' % (nbSan - nbCheck)


if __name__ == '__main__':
    # Parse command-line arguments
    argParser = argparse.ArgumentParser(description="Generate the defaultParams.json for tasks in FOLDERs.")

    argParser.add_argument('-r', '--recursive', help='Searches recursively for tasks in FOLDER(s)', action='store_true')
    argParser.add_argument('-v', '--verbose', help='Be more verbose', action='store_true')
    argParser.add_argument('-V', '--version', help='Print current version and exit', action='store_true')
    argParser.add_argument('folder', help='Task to generate for', nargs='*')

    args = argParser.parse_args()

    # Get genJson version
    try:
        # The version is the last commit modifying genJson in git
        VERSION = subprocess.check_output([
            '/usr/bin/env', 'git', 'log', '-n', '1',
            '--pretty=%H', '--', __file__],
            stderr=subprocess.STDOUT, cwd=SELFDIR,
            universal_newlines=True).strip()
    except:
        # Unable to get version from git, we just use a timestamp
        VERSION = 'stamp-%d' % int(time.time())

    if args.version:
        print VERSION
        sys.exit(0)
    elif len(args.folder) == 0:
        argParser.error("error: too few arguments")

    # If recursive, we recursively explore paths given for tasks
    if args.recursive:
        paths = []
        dirsToExplore = args.folder[:]
        while dirsToExplore != []:
            curDirsToExplore = dirsToExplore[:]
            dirsToExplore = []
            for d in curDirsToExplore:
                l = os.listdir(d)
                for f in l:
                    fulld = os.path.join(d, f)
                    if os.path.isdir(fulld):
                        if os.path.isdir(os.path.join(d, f, 'tests/')):
                            paths.append(fulld)
                        else:
                            dirsToExplore.append(fulld)

        if len(paths) == 0:
            print "No paths found."
            argParse.print_usage()
            sys.exit(1)
        else:
            print '*** Tasks found: ' + ', '.join(paths)
    else:
        paths = args.folder

    fatalErrors = 0
    tasksWithErrors = []

    for path in paths:
        retCode = processPath(path, args)
        if retCode > 0:
            tasksWithErrors.append(path)
            if retCode == 1:
                fatalErrors += 1

    if len(tasksWithErrors) > 0:
        print ''
        if len(tasksWithErrors) == 1:
            if tasksWithErrors[0] == '.':
                print "*** /!\ Task in current folder returned errors."
            else:
                print '*** /!\ Task in folder `%s` returned errors.' % tasksWithErrors[0]
        else:
            print "*** /!\ Some tasks returned errors:"
            print ', '.join(tasksWithErrors)
        if not args.verbose:
            print "Use -v switch to see the full JSON data and check for errors."
        if len(tasksWithErrors) > fatalErrors:
            # Not all task errors are fatal
            sys.exit(2)
        else:
            # All task errors are fatal (taskgrader not executing the task at all)
            sys.exit(1)
    else:
        print ''
        print "Completed without errors."
        sys.exit(0)
