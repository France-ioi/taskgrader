#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT


import argparse, glob, json, os, re, shutil, sys, subprocess, tempfile, time
from config import *

CFG_SELFDIR = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))


# TODO :: change all print statements

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
    f = open(os.path.join(CFG_SELFDIR, 'scripts', path), 'rb')
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
    defaultParams = {'rootPath': CFG_ROOTDIR,
                    'defaultToolCompParams': CFG_DEF_TOOLCOMPPARAMS,
                    'defaultToolExecParams': CFG_DEF_TOOLEXECPARAMS}

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
        (genDir, genFilename) = os.path.split(taskSettings['generator'])

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

        # We execute the generator to know which files it generates # TODO :: check for regressions
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
        extraDir = taskSettings['extraDir']
        # Extra tests
        if os.path.isdir(os.path.join(extraDir, 'all/')) and os.path.isdir(os.path.join(extraDir, 'python/')):
            # We have specific tests for python
            for f in globOfGlobs(extraDir, ['all/*.in', 'all/*.out']):
                defExtraTests.append({'name': 'all-' + os.path.basename(f),
                                      'path': os.path.join('$TASK_PATH', os.path.relpath(f, taskPath))})
            for f in globOfGlobs(taskPath, ['files/*.in', 'files/*.out']):
                defExtraTests.append({'name': 'py-' + os.path.basename(f),
                                      'path': '$TASK_PATH/' + os.path.relpath(f, taskPath)})
            defFilterTests = ['all-*.in']
            defFilterTestsPy = ['py-*.in']
        else:
            # Tests are the same for all languages
            for f in globOfGlobs(extraDir, ['*.in', '*.out']):
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

    # Handle overrideParams
    defaultParams.update(taskSettings.get('overrideParams', {}))

    return defaultParams


def genTestSolution(compParams, solId=1, solPath=None, solLang=None):
    """Generate the JSON decribing a solution."""
    if solPath:
        return {'id': 'testSolution%d' % solId,
                'compilationDescr': {
                    'language': solLang,
                    'files': [{'name': os.path.basename(solPath),
                               'path': solPath}],
                    'dependencies': '@defaultDependencies-%s' % solLang},
                'compilationExecution': compParams}
    else:
        # If no solution is given, we use `true.sh` default script
        return {'id': 'testSolution%d' % solId,
                'compilationDescr': {
                    'language': 'sh',
                    'files': [getScript('true.sh')],
                    'dependencies': []},
                'compilationExecution': compParams}


def genTestEvaluation(relPath, correctSolutions=[]):
    """Generate the JSON describing a test evaluation of a solution."""

    if len(correctSolutions) > 0:
        testSolutions = []
        testExecutions = []
        # There are specific solutions to test
        for (i, sol) in enumerate(correctSolutions):
            testSolutions.append(genTestSolution(CFG_TESTSOLPARAMS, i, sol['path'], sol['language']))
            testExecutions.append({
                'id': 'testExecution%d' % i,
                'idSolution': 'testSolution%d' % i,
                'filterTests': '@defaultFilterTests',
                'runExecution': CFG_TESTSOLPARAMS})
    else:
        # There's no real solution to test, we just test a dummy one
        testSolutions = [genTestSolution(CFG_TESTSOLPARAMS, 1)]

        testExecutions = [{'id': 'testExecution1',
            'idSolution': 'testSolution1',
            'filterTests': '@defaultFilterTests',
            'runExecution': CFG_TESTSOLPARAMS}]

    testEvaluation = {
            'rootPath': CFG_ROOTDIR,
            'taskPath': '$ROOT_PATH/%s' % relPath,
            'generators': ['@defaultGenerator'],
            'generations': ['@defaultGeneration'],
            'extraTests': '@defaultExtraTests',
            'sanitizer': '@defaultSanitizer',
            'checker': '@defaultChecker',
            'solutions': testSolutions,
            'executions': testExecutions}

    return testEvaluation

if __name__ == '__main__':
    # Parse command-line arguments
    argParser = argparse.ArgumentParser(description="Generate the defaultParams.json for tasks in FOLDERs.")

    argParser.add_argument('-r', '--recursive', help='Searches recursively for tasks in FOLDER(s)', action='store_true')
    argParser.add_argument('-v', '--verbose', help='Be more verbose', action='store_true')
    argParser.add_argument('folder', help='Task to generate for', nargs='+')

    args = argParser.parse_args()

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
            print '* Tasks found: ' + ', '.join(paths)
    else:
        paths = args.folder

    tasksWithErrors = []

    for path in paths:
        print '* Generating defaultParams for ' + path
        # Settings for the task
        taskSettings = {}
        taskSettings.update(CFG_DEF_TASKSETTINGS)
        try:
            taskSettings.update(json.load(open(os.path.join(path, 'taskSettings.json'), 'r')))
        except:
            pass

        defaultParams = genDefaultParams(path, taskSettings)
        json.dump(defaultParams, open(os.path.join(path, 'defaultParams.json'), 'w'))
        print ''
        if args.verbose:
            print '* Generated defaultParams'
            print json.dumps(defaultParams)
            print ''

        # Make test evaluation
        taskPath = os.path.relpath(path, CFG_ROOTDIR)
        testEvaluation = genTestEvaluation(taskPath, taskSettings.get('correctSolutions', []))
        testEvaluation['extraParams'] = defaultParams # We input directly the default params
        if args.verbose:
            print '* Generated test evaluation'
            print json.dumps(testEvaluation)
            print ''

        # Execute test evaluation
        print '* Auto-test with taskgrader'
        proc = subprocess.Popen([CFG_TASKGRADER], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        (procOut, procErr) = proc.communicate(json.dumps(testEvaluation))
        if args.verbose:
            print '* Test evaluation report'
            print procOut

        # Read output JSON
        try:
            outJson = json.loads(procOut)
        except:
            tasksWithErrors.append(path)
            continue

        if len(taskSettings.get('taskSettings', [])) > 0:
            # Check execution of the "correct solutions"
            # Their test was integrated in the test evaluation
            cError = False
            if len(outJson['executions']) != len(taskSettings['correctSolutions']):
                print "Test failed : %d correct solutions tested / %d total" % (len(outJson['executions']), len(taskSettings['correctSolutions']))
                cError = True
            for execution in outJson['executions']:
                if execution['name'][:13] != "testExecution":
                    continue
                # Get corresponding solution
                solData = taskSettings['correctSolutions'][int(execution['name'][13:])]
                nbOk = 0
                nbTotal = len(execution['testsReports'])
                # Check grade for each test
                for test in execution['testsReports']:
                    try:
                        testGrade = int(test['checker']['stdout']['data'].split()[0])
                        if testGrade == solData['grade']:
                            nbOk += 1
                        else:
                            print "Got grade %d instead of %d" % (testGrade, solData['grade'])
                    except:
                        print "Error reading test"
                if nbOk != nbTotal:
                    print "Test failed on %s: %d/%d grades incorrect" % (solData['path'], nbTotal-nbOk, nbTotal)
                    cError = True
                if nbTotal != solData.get('nbtests', nbTotal):
                    print "Test failed on %s: %d tests done / %d tests expected" % (solData['path'], nbTotal, solData['nbtests'])
                    cError = True
            if cError:
                tasksWithErrors.append(path)
                print procOut
            else:
                print "Test successful on correctSolutions."
        else:
            # Just check the dummy solution executed successfully at least once
            try:
                exitCode = outJson['executions'][0]['testsReports'][0]['execution']['exitCode']
            except:
                exitCode = -1
            if exitCode != 0:
                tasksWithErrors.append(path)

    if len(tasksWithErrors) > 0:
        print ''
        print "*** /!\ Some tasks returned errors:"
        print ', '.join(tasksWithErrors)
        sys.exit(1)
