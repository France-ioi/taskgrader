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



import glob, hashlib, json, os, shutil, sys, subprocess
import pickle, random # Temporary

CFG_BASEDIR = './'
CFG_BUILDSDIR = CFG_BASEDIR + 'builds/'
CFG_REPODIR = CFG_BASEDIR + 'repo/'
CFG_CACHEDIR = CFG_BASEDIR + 'cache/'

CFG_ISOLATEBIN = CFG_BASEDIR + 'isolate'
CFG_RIGHTSBIN = CFG_BASEDIR + 'rights'

class dictWithVars(dict):
    """Class representing JSON data with some variables in it.
    Extension of the Python dict class; the initDict argument allows to
    initialize its internal value to a dict.
    varData represents the variable data; all values written as '@varname' in
    the dict will be replaced by varData['varname']."""

    def __init__(self, varData, initDict={}, *args, **kwargs):
        self.varData = varData
        super(dictWithVars, self).__init__(*args, **kwargs)
        super(dictWithVars, self).update(initDict)

    def __getvalue__(self, val):
        """Filters val to check whether it's a variable or not."""
        if type(val) is str and len(val) > 0 and val[0] == '@':
            # It's a variable, we replace it with the JSON data
            # It will return an error if the variable doesn't exist, it's intended
            return self.varData[val[1:]]
        elif type(val) is dict:
            # It's a dict, we replace it with a dictWithVars
            return dictWithVars(self.varData, initDict=val)
        elif type(val) is list:
            # It's a list, we filter the values in it
            return map(self.__getvalue__, val)
        else:
            return val

    def __getitem__(self, key):
        # We only need to change how values are returned
        return self.__getvalue__(super(dictWithVars, self).__getitem__(key))


def isExecError(executionReport):
    """Returns whether an execution returned an error according to its exit code."""
    return (executionReport['exitCode'] != 0)


def getFile(fileDescr, workingDir):
    """Fetch a file contents from a fileDescr object into workingDir.
    If getCache is True, also lookup cache for related cached files."""

    if os.path.isfile(workingDir + fileDescr['name']):
        # File already exists
        raise Exception()

    if fileDescr.has_key('content'): # Content given in descr
        open(workingDir + fileDescr['name'], 'w').write(fileDescr['content'])
    else: # Get file by path
        os.symlink(CFG_REPODIR + fileDescr['path'], workingDir + fileDescr['name'])
    return None


def getCacheDir(files, cacheType, inputFiles=[]):
    """For a list of source files and the type (compilation or execution),
    returns a tuple containing:
    -whether some related files have been cached
    -where to store/retrieve cache files."""
    fileIdList = []
    fileHashList = []
    # We build a list of identifiers for each source file and compute their md5
    for fileDescr in files:
        if fileDescr.has_key('content'):
            # File content is given, we use the name given and the hash as reference
            md5sum = hashlib.md5(fileDescr['content']).hexdigest()
            fileIdList.append("file:%s:%s" % (fileDescr['name'], md5sum))
            fileHashList.append(md5sum)
        else:
            # File path is given, we use the path as reference
            fileIdList.append("path:%s" % fileDescr['path'])
            fileHashList.append(hashlib.md5(open(CFG_REPODIR + fileDescr['path'], 'rb').read()).hexdigest())

    # We add identifiers for input files (local name and md5sum)
    for f in inputFiles:
        fileIdList.append("input:%s" % os.path.basename(f))
        fileHashList.append(hashlib.md5(open(f, 'rb').read()).hexdigest())

    fileIdList.sort()
    fileHashList.sort() # Both lists won't be sorted the same but it's not an issue

    # This will be the ID string in the database, containing the cache type and the source files list
    filesId = "cache:%s;%s" % (cacheType, ";".join(fileIdList))

    # TODO :: vraie DB quand le programme sera complet
    # Read cache information from database
    try:
        database = pickle.load(open('database.pickle', 'r'))
    except:
        database = {}
    if database.has_key(filesId):
        # This list of files already exists in the database
        (dbId, dbHashList) = database[filesId]
        if dbHashList == fileHashList and os.path.isfile("%s%s/cache.ok" % (CFG_CACHEDIR, dbId)):
            # MD5 hashes are good
            return (True, "%s%s/" % (CFG_CACHEDIR, dbId))
        else:
            # MD5 hashes changed, update database, invalidate cache
            database[filesId] = (dbId, fileHashList)
            pickle.dump(database, open('database.pickle', 'w'))
            for f in os.listdir("%s%s/" % (CFG_CACHEDIR, dbId)):
                os.remove("%s%s/%s" % (CFG_CACHEDIR, dbId, f))
            return (False, "%s%s/" % (CFG_CACHEDIR, dbId))
    else:
        # New entry in database
        newId = len(database)
        database[filesId] = (newId, fileHashList)
        pickle.dump(database, open('database.pickle', 'w'))
        os.mkdir("%s%s/" % (CFG_CACHEDIR, newId))
        return (False, "%s%s/" % (CFG_CACHEDIR, newId))


def capture(path, name='', truncateSize=-1):
    """Capture a file descriptor contents for inclusion into the output json."""
    report = {'name': name,
              'sizeKb': os.path.getsize(path) / 1024}
    fd = open(path, 'r')
    if truncateSize > -1:
        report['data'] = fd.read(truncateSize)
        report['wasTruncated'] = (len(fd.read(1)) > 0)
    else:
        report['data'] = fd.read()
        report['wasTruncated'] = False
    fd.close()
    return report


def execute(executionParams, cmdLine, workingDir, stdinFile=None, stdoutFile=None, isolate=True):
    """Execute a command line and build the report."""
    # Values copied from the arguments
    report = {'timeLimitMs': executionParams['timeLimitMs'],
            'memoryLimitKb': executionParams['memoryLimitKb'],
            'commandLine': cmdLine,
            'wasCached': False}

    if stdoutFile == None:
        stdoutFile = workingDir + 'stdout.out'

    if isolate:
        # Initialize isolate box
        initProc = subprocess.Popen([CFG_ISOLATEBIN, '--init'], stdout=subprocess.PIPE, cwd=workingDir)
        (isolateDir, isolateErr) = initProc.communicate()
        initProc.wait()
        # isolatePath will be the path of the sandbox, as given by isolate
        isolateDir = isolateDir.strip() + '/box/'

        # Build isolate command line
        isolatedCmdLine  = CFG_ISOLATEBIN
        isolatedCmdLine += ' --meta=' + os.getcwd() + '/' + workingDir + 'isolate.meta'
        if executionParams['timeLimitMs'] > 0:
            isolatedCmdLine += ' --time=' + str(executionParams['timeLimitMs'] / 1000.)
        if executionParams['memoryLimitKb'] > 0:
            isolatedCmdLine += ' --mem=' + str(executionParams['memoryLimitKb'])
        if stdinFile:
            shutil.copy(stdinFile, isolateDir + 'isolated.stdin')
            isolatedCmdLine += ' --stdin=isolated.stdin'
        isolatedCmdLine += ' --stdout=isolated.stdout --stderr=isolated.stderr'
        isolatedCmdLine += ' --run -- ' + cmdLine

        # Copy files from working directory to sandbox
        for f in os.listdir(workingDir):
            shutil.copy(workingDir + f, isolateDir + f)

        print isolatedCmdLine
        open(workingDir + 'isolate.meta', 'w')

        # Execute the isolated program
        proc = subprocess.Popen(isolatedCmdLine.split(), cwd=workingDir)
        proc.wait()

        # Set file rights so that we can access the files
        rightsProc = subprocess.Popen([CFG_RIGHTSBIN])
        rightsProc.wait()

        # Copy back the files from sandbox
        for f in os.listdir(isolateDir):
            shutil.copy(isolateDir + f, workingDir + f)
        shutil.copy(isolateDir + 'isolated.stdout', stdoutFile)

        # Get metadata from isolate execution
        isolateMeta = {}
        for l in open(workingDir + 'isolate.meta', 'r').readlines():
            [name, val] = l.split(':', 1)
            isolateMeta[name] = val.strip()

        # Generate execution report
        if isolateMeta.has_key('time'):
            report['timeTakenMs'] = float(isolateMeta['time'])*1000
        else:
            report['timeTakenMs'] = -1
        report['wasKilled'] = isolateMeta.has_key('killed')
        if isolateMeta.has_key('exitcode'):
            report['exitCode'] = int(isolateMeta['exitcode'])
        else:
            report['exitCode'] = proc.returncode

        report['stdout'] = capture(workingDir + 'isolated.stdout', name='stdout',
                truncateSize=executionParams['stdoutTruncateKb'] * 1024)
        report['stderr'] = capture(workingDir + 'isolated.stderr', name='stderr',
                truncateSize=executionParams['stderrTruncateKb'] * 1024)

        # Cleanup sandbox
        cleanProc = subprocess.Popen([CFG_ISOLATEBIN, '--cleanup'], cwd=workingDir)
        cleanProc.wait()
    else:
        # We don't use isolate
        if stdinFile:
            stdinHandle = open(stdinFile, 'r')
        else:
            stdinHandle = None
        proc = subprocess.Popen(cmdLine.split(), stdin=stdinHandle, stdout=open(stdoutFile, 'w'),
                stderr=open(workingDir + 'stderr.out', 'w'), cwd=workingDir)

        proc.wait()

        # Generate execution report
        report['timeTakenMs'] = -1 # We don't know
        report['wasKilled'] = False
        report['exitCode'] = proc.returncode

        report['stdout'] = capture(stdoutFile, name='stdout',
                truncateSize=executionParams['stdoutTruncateKb'] * 1024)
        report['stderr'] = capture(workingDir + 'stderr.out', name='stderr',
                truncateSize=executionParams['stderrTruncateKb'] * 1024)

    filesReports = []
    for globf in executionParams['getFiles']:
        for f in glob.glob(workingDir + globf):
            # Files captured are always truncated at 1MB
            filesReports.append(capture(f, name=os.path.basename(f), truncateSize=1024*1024))
    report['files'] = filesReports

    print report # TODO enlever

    return report


def cachedExecute(executionParams, cmdLine, workingDir, cacheData, stdinFile=None, stdoutFile='stdout.out', outputFiles=[]):
    """Get the results from execution of a program, either by fetching them
    from cache, or by actually executing the program."""
    if executionParams['useCache']:
        (cacheStatus, cacheDir) = cacheData
        if cacheStatus:
            # Results are in cache, we fetch the report
            report = json.load(open("%srunExecution.json" % cacheDir, 'r'))
            report['wasCached'] = True
            # We load cached results (as symlinks)
            for g in outputFiles:
                for f in glob.glob(cacheDir + g):
                    os.symlink(f, workingDir + os.path.basename(f))
        else:
            # We execute again the program
            report = execute(executionParams, cmdLine, workingDir, stdinFile=stdinFile)
            # We save results to cache if execution was successful
            if not isExecError(report):
                for g in outputFiles:
                    for f in glob.glob(cacheDir + g):
                        shutil.copy(f, workingDir)
                json.dump(report, open("%srunExecution.json" % cacheDir, 'w'))
                open("%scache.ok" % cacheDir, 'w')
    else:
        # We don't use cache at all
        report = execute(executionParams, cmdLine, workingDir, stdinFile=stdinFile)

    return report


def compile(compilationDescr, executionParams, workingDir, name='executable'):
    """Effectively compile a program, not using cache (probably because
    there's no cached version)."""
    # We fetch source files into the workingDir
    sourceFiles = []
    for source in compilationDescr['files']: # Fetch source files
        getFile(source, workingDir)
        sourceFiles.append(source['name'])

    # We fetch dependencies into the workingDir
    for dep in compilationDescr['dependencies']: # Fetch dependencies
        getFile(dep, workingDir)

    # We compile according to the source type
    if compilationDescr['language'] == 'c':
        cmdLine = "gcc -W -Wall -O2 -o %s.exe %s" % (name, ' '.join(sourceFiles))
        report = execute(executionParams, cmdLine, workingDir, isolate=False)
    elif compilationDescr['language'] == 'cpp':
        cmdLine = "g++ -W -Wall -O2 -o %s.exe %s" % (name, ' '.join(sourceFiles))
        report = execute(executionParams, cmdLine, workingDir, isolate=False)
    elif compilationDescr['language'] == 'py' or compilationDescr['language'] == 'py3':
        # Python is not "compiled", we just write a shell script to execute it
        if compilationDescr['language'] == 'py':
            open(name + '.exe', 'w').write("#!/bin/sh\npython2 %s" % ' '.join(sourceFiles))
        else:
            open(name + '.exe', 'w').write("#!/bin/sh\npython3 %s" % ' '.join(sourceFiles))
        # We build a dummy report
        report = {'timeLimitMs': executionParams['timeLimitMs'],
                'memoryLimitKb': executionParams['memoryLimitKb'],
                'cmdLine': '[shell script built]',
                'timeTakenMs': 0,
                'wasKilled': False,
                'wasCached': False,
                'exitCode': 0,
                'stdout': '',
                'stderr': '',
                'files': ''}
    # TODO :: compilation d'autres langages : Java, Pascal, Caml
    return report


def cachedCompile(compilationDescr, executionParams, workingDir, cacheData, name='executable'):
    """Get the compiled version of a program, either by fetching it from cache
    if possible, either by compiling it."""
    if executionParams['useCache']:
        (cacheStatus, cacheDir) = cacheData
        if cacheStatus:
            # We load the report and executable from cache
            os.symlink("%s%s.exe" % (cacheDir, name), "%s%s.exe" % (workingDir, name))
            report = json.load(open("%scompilationExecution.json" % cacheDir, 'r'))
            report['wasCached'] = True
        else:
            # No current cache, we compile
            report = compile(compilationDescr, executionParams, workingDir, name)
            # We cache the results if compilation was successful
            if not isExecError(report):
                shutil.copy("%s%s.exe" % (workingDir, name), cacheDir)
                json.dump(report, open("%scompilationExecution.json" % cacheDir, 'w'))
                open("%scache.ok" % cacheDir, 'w')
    else:
        # We don't use cache at all
        report = compile(compilationDescr, compilationExecution, workingDir, name)

    return report


def compileAndRun(compileAndRunParams, workingDir, cacheType=None, stdinFile=None, inputFiles=[], outputFiles=[], name='executable'):
    """Compile a program and then run it.
    cacheType argument tells what we should cache (or fetch from cache), either
    the compiled executable or the output of the executable.
    outputFiles tells which files are considered as output of the run and
    should thus be cached."""
    report = {}
    if cacheType == None:
        # We compile and run without any cache
        report['compilationExecution'] = compile(compileAndRunParams['compilationDescr'],
                                             compileAndRunParams['compilationExecution'],
                                             workingDir, name)
        report['runExecution'] = execute('%s%s.exe' % (workingDir, name), compileAndRunParams['runExecution'], workingDir, stdinFile=stdinFile)
    else:
        # We fetch the cache status
        (compCacheStatus, compCacheDir) = getCacheDir(compileAndRunParams['compilationDescr']['files'], cacheType)

        report['compilationExecution'] = cachedCompile(compileAndRunParams['compilationDescr'],
                compileAndRunParams['compilationExecution'], workingDir,
                (compCacheStatus, compCacheDir), name, stdinFile=stdinFile)

        if cacheType == 'compilation':
            # We only use cache for compilation
            report['runExecution'] = execute('%s%s.exe' % (workingDir, name), compileAndRunParams['runExecution'], workingDir, stdinFile=stdinFile)
        elif cacheType == 'execution':
            # We use cache for both compilation and execution
            (execCacheStatus, execCacheDir) = getCacheDir(compileAndRunParams['compilationDescr']['files'], cacheType, inputFiles=inputFiles)
            report['runExecution'] = cachedExecute('%s%s.exe' % (workingDir, name),
                    compileAndRunParams['runExecution'], workingDir, outputFiles,
                    (execCacheStatus, execCacheDir), outputFiles=outputFiles, stdinFile=stdinFile)

    return report


def evaluation(evaluationParams):
    """Full evaluation process."""

    if evaluationParams.has_key('mergeWithJson'):
        # We load a "preprocessing" JSON file
        if type(evaluationParams['mergeWithJson']) is str:
            varData = json.load(open(evaluationParams['mergeWithJson'], 'r'))
        else:
            varData = evaluationParams['mergeWithJson']
        evaluationParams = dictWithVars(varData, initDict=evaluationParams)
    else:
        try:
            varData = json.load(open(evaluationParams['taskPath'] + 'defaultParams.json', 'r'))
            evaluationParams = dictWithVars(varData, initDict=evaluationParams)
        except:
            pass

    baseWorkingDir = evaluationParams['rootPath'] + evaluationParams['outputPath']
    os.mkdir(baseWorkingDir)
    report = {}

    os.mkdir(baseWorkingDir + "tests/")

    errorSoFar = False


    # *** Generators
    os.mkdir(baseWorkingDir + "generators/")
    report['generators'] = []
    generatorsFiles = {} # Source files of solutions, need this for the generations
    for gen in evaluationParams['generators']:
        genDir = "%sgenerators/%s/" % (baseWorkingDir, gen['id'])
        os.mkdir(genDir)
        # We only compile the generator
        genReport = cachedCompile(gen['compilationDescr'], gen['compilationExecution'],
               genDir, getCacheDir(gen['compilationDescr']['files'], 'compilation'), 'generator')
        errorSoFar = errorSoFar or isExecError(genReport)
        report['generators'] = (gen['id'], genReport)
        generatorsFiles[gen['id']] = gen['compilationDescr']['files']


    # *** Generations
    os.mkdir(baseWorkingDir + "generations/")
    report['generations'] = []
    for gen in evaluationParams['generations']:
        genDir = "%sgenerations/%s/" % (baseWorkingDir, gen['id'])
        os.mkdir(genDir)
        if gen.has_key('testCases'):
            # We have specific test cases to generate
            for tc in gen['testCases']:
                genReport = {'id': "%s.%s" % (gen['id'], tc['name'])}
                if gen.has_key('idOutputGenerator'):
                    # We also have an output generator, we generate `name`.in and `name`.out
                    shutil.copy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idGenerator'], genDir + 'generator.exe')
                    genReport['generatorExecution'] = cachedExecute(gen['genExecution'], "generator.exe %s" % tc['params'], genDir,
                            getCacheDir(generatorsFiles[gen['idGenerator']], 'execution:' + tc['params']),
                            stdoutFile=tc['name'] + '.in',
                            outputFiles=[tc['name'] + '.in'])
                    shutil.copy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idOutputGenerator'], genDir + 'outgenerator.exe')
                    genReport['outputGeneratorExecution'] = cachedExecute(gen['outGenExecution'], "outgenerator.exe %s" % tc['params'], genDir,
                            getCacheDir(generatorsFiles[gen['idOutputGenerator']], 'execution:' + tc['params']),
                            stdoutFile=tc['name'] + '.out',
                            outputFiles=[tc['name'] + '.out'])
                    shutil.copy(tc['name'] + '.in', baseWorkingDir + 'tests/' + tc['name'] + '.in')
                    shutil.copy(tc['name'] + '.out', baseWorkingDir + 'tests/' + tc['name'] + '.out')
                    errorSoFar = errorSoFar or isExecError(genReport['generatorExecution']) or isExecError(genReport['outputGeneratorExecution'])
                else:
                    # We only have one generator, we assume `name` is the name of the test file to generate
                    shutil.copy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idGenerator'], genDir + 'generator.exe')
                    genReport['generatorExecution'] = cachedExecute(gen['genExecution'], "generator.exe %s" % tc['params'], genDir,
                            getCacheDir(generatorsFiles[gen['idGenerator']], 'execution:' + tc['params']),
                            stdoutFile=tc['name'],
                            outputFiles=[tc['name']])
                    shutil.copy(tc['name'], baseWorkingDir + 'tests/' + tc['name'])
                    errorSoFar = errorSoFar or isExecError(genReport['generatorExecution'])
                report['generations'].append(genReport)
                
        else:
            # We generate the test cases just by executing the generators
            genReport = {'id': gen['id']}
            shutil.copy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idGenerator'], genDir + 'generator.exe')
            genReport['generatorExecution'] = cachedExecute(gen['genExecution'], "generator.exe", genDir,
                    getCacheDir(generatorsFiles[gen['idGenerator']], 'execution'), outputFiles=['*.in', '*.out'])
            errorSoFar = errorSoFar or isExecError(genReport['generatorExecution'])
            if gen.has_key('idOutputGenerator'):
                # We also have an output generator
                shutil.copy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idOutputGenerator'], genDir + 'outgenerator.exe')
                genReport['outputGeneratorExecution'] = cachedExecute(gen['outGenExecution'], "outgenerator.exe" % gen['idOutputGenerator'], genDir,
                        getCacheDir(generatorsFiles[gen['idOutputGenerator']], 'execution'), outputFiles=['*.out'])
                errorSoFar = errorSoFar or isExecError(genReport['outputGeneratorExecution'])
            report['generations'].append(genReport)
            # We copy the generated test files
            for f in (glob.glob(genDir + '*.in') + glob.glob(genDir + '*.out')):
                shutil.copy(f, baseWorkingDir + 'tests/' + os.path.basename(f))

    # We add extra tests
    for et in evaluationParams['extraTests']:
        getFile(et, baseWorkingDir + "tests/")

    # *** Sanitizer
    os.mkdir(baseWorkingDir + "sanitizer/")
    report['sanitizer'] = cachedCompile(evaluationParams['sanitizer']['compilationDescr'],
            evaluationParams['sanitizer']['compilationExecution'],
            baseWorkingDir + "sanitizer/",
            getCacheDir(evaluationParams['sanitizer']['compilationDescr']['files'], 'compilation'),
            'sanitizer')
    errorSoFar = errorSoFar or isExecError(report['sanitizer'])

    # *** Checker
    os.mkdir(baseWorkingDir + "checker/")
    report['checker'] = cachedCompile(evaluationParams['checker']['compilationDescr'],
            evaluationParams['checker']['compilationExecution'],
            baseWorkingDir + "checker/",
            getCacheDir(evaluationParams['checker']['compilationDescr']['files'], 'compilation'),
            'checker')
    errorSoFar = errorSoFar or isExecError(report['sanitizer'])


    # Did we encounter an error so far?
    if errorSoFar:
        raise Exception()


    # *** Solutions
    os.mkdir(baseWorkingDir + "solutions/")
    report['solutions'] = []
    solutionsFiles = {} # Source files of solutions, need this for the evaluations
    solutionsWithErrors = []
    for sol in evaluationParams['solutions']:
        solDir = "%ssolutions/%s/" % (baseWorkingDir, sol['id'])
        os.mkdir(solDir)
        # We only compile the solution
        solReport = cachedCompile(sol['compilationDescr'], sol['compilationExecution'],
               solDir, getCacheDir(sol['compilationDescr']['files'], 'compilation'), 'solution')
        report['solutions'].append(solReport)
        solutionsFiles[sol['id']] = sol['compilationDescr']['files']
        if isExecError(solReport):
            # We keep a list of solutions with errors
            solutionsWithErrors.append(sol['id'])

    # *** Executions
    os.mkdir(baseWorkingDir + "executions/")
    report['executions'] = []
    for test in evaluationParams['executions']:
        if test['idSolution'] in solutionsWithError:
            # This solution didn't compile
            continue

        mainTestReport = {'name': test['idSolution'], 'testsReports': []}
        testDir = "%sexecutions/%s.%s/" % (baseWorkingDir, test['idSolution'], test['id'])
        os.mkdir(testDir)

        # Files to test as input
        testFiles = []
        for filterGlob in test['filterTests']:
            testFiles.extend(glob.glob(testDir + filterGlob))

        for tf in testFiles:
            # We execute everything for each test file tf
            if '.' in os.path.basename(tf):
                baseTfName = os.path.basename(tf).split('.')[:-1]
            else:
                baseTfName = os.path.basename(tf)
            
            subTestReport = {'name': baseTfName}
            # We execute the sanitizer
            shutil.copy(baseWorkingDir + 'sanitizer/sanitizer.exe', testDir + 'sanitizer.exe')
            subTestReport['sanitizer'] = cachedExecute(evaluationParams['checker']['runExecution'],
                    'sanitizer.exe',
                    testDir,
                    getCacheDir(evaluationParams['sanitizer']['compilationDescr']['files'], 'execution', inputFiles=[tf]),
                    stdinFile=tf, stdoutFile=testDir + baseTfName + '.in',
                    outputFiles=[testDir + baseTfName + '.in'])
            if isExecError(subTestReport['sanitizer']):
                # Sanitizer didn't work, we skip this file
                continue
            # We execute the solution
            os.symlink("%ssolutions/%s/solution.exe" % (baseWorkingDir, test['idSolution']), testDir + 'solution.exe')
            subTestReport['execution'] = cachedExecute(test['runExecution'], 'solution.exe', testDir,
                    getCacheDir(solutionsFiles[test['idSolution']], 'execution', inputFiles=[testDir + baseTfName + '.in']),
                    stdinFile=testDir + baseTfName + '.in', stdoutFile=testDir + baseTfName + '.out',
                    outputFiles=[testDir + baseTfName + '.out'])
            if isExecError(subTestReport['execution']):
                # Solution returned an error, no need to check
                continue
            # We execute the checker
            os.symlink(baseWorkingDir + 'checker/checker.exe', testDir + 'checker.exe')
            subTestReport['checker'] = cachedExecute(evaluationParams['checker']['runExecution'],
                    "checker.exe", testDir,
                    getCacheDir(evaluationParams['checker']['compilationDescr']['files'], 'execution', inputFiles=[testDir + baseTfName + '.out']),
                    stdinFile=testDir + baseTfName + '.out', stdoutFiles=testDir + baseTfName + '.ok',
                    outputFiles=[testDir + baseTfName + '.ok'])
            mainTestReport['testsReports'].append(subTestReport)

        report['executions'].append(testReport)

    return report


if __name__ == '__main__':
    inJson = json.load(sys.stdin)
    json.dump(evaluation(inJson), sys.stdout)
