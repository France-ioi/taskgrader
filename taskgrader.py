#!/usr/bin/env -v python

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



import glob, hashlib, json, os, resource, shutil, subprocess
import pickle # Temporary

CFG_REPODIR = 'repo/'
CFG_CACHEDIR = 'cache/'


def getFile(fileDescr, workingDir):
    """Fetch a file contents from a fileDescr object into workingDir.
    If getCache is True, also lookup cache for related cached files."""
    if fileDescr.has_key('content'): # Content given in descr
        open(workingDir + fileDescr['name'], 'w').write(fileDescr['content'])
    else: # Get file by path
        os.symlink(repoDir + fileDescr['path'], workingDir + fileDescr['name'])
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
        if dbHashList == fileHashList:
            # MD5 hashes are good
            return (True, "%s%s/" % (CFG_CACHEDIR, dbId))
        else:
            # MD5 hashes changed, update database, invalidate cache
            database[filesId] = (dbId, fileHashList)
            pickle.dump(database, open('database.pickle', 'w'))
            for f in os.listDir("%s%s/" % (CFG_CACHEDIR, dbId)):
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


def execute(executionParams, cmdLine, workingDir):
    """Execute a command line and build the report."""
    # Values copied from the arguments
    executionReport = {'timeLimitMs': executionParams['timeLimitMs'],
                       'memoryLimitKb': executionParams['memoryLimitKb'],
                       'commandLine': cmdLine}
    # TODO : wrapper
    start_res = resource.getrusage(resource.RUSAGE_CHILDREN)
    proc = subprocess.Popen(cmdLine.split(), stdout=open('stdout.out', 'w'),
            stderr=open('stderr.out', 'w'), cwd=workingDir)

    proc.wait()
    end_res = resource.getrusage(resource.RUSAGE_CHILDREN)

    # Generate execution report
    executionReport['timeTakenMs'] = (end_res.ru_utime + end_res.ru_stime) - (start_res.ru_utime + start_res.ru_utime)
    executionReport['wasKilled'] = False # TODO avec le wrapper
    executionReport['wasCached'] = False
    executionReport['exitCode'] = proc.returncode
    executionReport['stdout'] = capture('stdout.out', name='stdout',
            truncateSize=executionParams['stdoutTruncateKb'] * 1024)
    executionReport['stderr'] = capture('stderr.out', name='stderr',
            truncateSize=executionParams['stderrTruncateKb'] * 1024)
    filesReports = []
    for globf in executionParams['getFiles']:
        for f in glob.glob(workingDir + globf):
            filesReports.append(capture(f, name=os.path.basename(f)))
            # TODO :: truncateSize manquant dans la spec ?
    executionReport['files'] = filesReports


def cachedExecute(executionParams, cmdLine, workingDir, cacheData, outputFiles=[], compilationReport=None):
    """Get the results from execution of a program, either by fetching them
    from cache, or by actually executing the program."""
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
        report = execute(executionParams, cmdLine, workingDir)
        # We save results to cache
        for g in outputFiles:
            for f in glob.glob(cacheDir + g):
                shutil.copy(f, workingDir)
        # We copy reports in cache
        json.dump(report, open("%srunExecution.json" % cacheDir, 'r'))
        if compilationReport:
            json.dump(compilationReport, open("%scompilationExecution.json" % cacheDir, 'r'))
    return report


def compile(compilationDescr, executionParams, workingDir, name='executable'):
    """Compile a program."""
    # We fetch source files into the workingDir
    sourceFiles = []
    for source in compilationDescr['files']: # Fetch source files
        getFile(source, workingDir)
        sourceFiles.append(source['name'])

    # We fetch dependencies into the workingDir
    for dep in compilationDescr['dependencies']: # Fetch dependencies
        getFile(dep, workingDir)

    # We compile according to the source type
    if compilationDescr['language'] == 'cpp':
        cmdLine = "g++ -W -Wall -O2 -o %s.exe %s" % (name, ' '.join(sourceFiles))
        report = execute(executionParams, cmdLine, workingDir)
    # TODO :: compilation d'autres langages
    return report


def cachedCompile(compilationDescr, executionParams, workingDir, cacheData, name='executable'):
    """Get the compiled version of a program, either by fetching it from cache
    if possible, either by compiling it."""
    (cacheStatus, cacheDir) = cacheData
    if cacheStatus:
        # We load the report and executable from cache
        os.symlink("%s%s.exe" % (cacheDir, name), "%s%s.exe" % (workingDir, name))
        report = json.load(open("%scompilationExecution.json" % cacheDir, 'r'))
        report['wasCached'] = True
    else:
        # No current cache, we compile
        report = compile(compilationDescr, compilationExecution, workingDir, name)
        # We cache the results
        shutil.copy("%s%s.exe" % (workingDir, name), cacheDir)
        json.dump(report, open("%scompilationExecution.json" % cacheDir, 'r'))

    return report


def compileAndRun(compileAndRunParams, workingDir, cacheType=None, inputFiles=[], outputFiles=[], name='executable'):
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
                                             workingDir,
                                             name)
        report['runExecution'] = execute('%s%s.exe' % (workingDir, name), compileAndRunParams['runExecution'], workingDir)
    else:
        # We fetch the cache status
        (compCacheStatus, compCacheDir) = getCacheDir(compileAndRunParams['compilationDescr']['files'], cacheType)

        if cacheType == 'compilation':
            # We only use cache for compilation
            report['compilationExecution'] = cachedCompile(compileAndRunParams['compilationDescr'],
                    compileAndRunParams['compilationExecution'], workingDir,
                    (compCacheStatus, compCacheDir), name)
            report['runExecution'] = execute('%s%s.exe' % (workingDir, name), compileAndRunParams['runExecution'], workingDir)
        elif cacheType == 'execution':
            # We use cache for both compilation and execution
            (execCacheStatus, execCacheDir) = getCacheDir(compileAndRunParams['compilationDescr']['files'], cacheType, inputFiles=inputFiles)
            if execCacheStatus:
                # We load compilation report from results cache (we want the compilation
                # report corresponding to the run whose results we're fetching from cache)
                report['compilationExecution'] = json.load(open("%scompilationExecution.json" % execCacheDir, 'r'))
                report['compilationExecution']['wasCached'] = True
            else:
                # We will need to execute again the program, so we fetch it
                report['compilationExecution'] = cachedCompile(compileAndRunParams['compilationDescr'],
                        compileAndRunParams['compilationExecution'], workingDir,
                        (compCacheStatus, compCacheDir), name)

            # cachedExecute will do the rest
            report['runExecution'] = cachedExecute('%s%s.exe' % (workingDir, name),
                    compileAndRunParams['runExecution'], workingDir, outputFiles,
                    (execCacheStatus, execCacheDir), outputFiles)

    return report


def evaluation(evaluationParams):
    baseWorkingDir = evaluationParams['rootPath'] + evaluationParams['output_path']
    os.mkdir(baseWorkingDir)
    report = {}

    # *** Generator_in
    os.mkdir(baseWorkingDir + "generator_in/")
    report['generator_in'] = compileAndRun(evaluationParams['generator_in'],
            baseWorkingDir + "generator_in/",
            cacheType='execution', outputFiles=['*.in'], name='generator_in')

    # TODO :: ajouter fichiers in supplémentaires (spec ?)

    # *** Generator_out
    os.mkdir(baseWorkingDir + "generator_out/")
    # We copy *.in files from generator_in
    for f in glob.glob(baseWorkingDir + "generator_in/*.in"):
        os.symlink(f, baseWorkingDir + "generator_out/" + os.path.basename(f))
    report['generator_out'] = compileAndRun(evaluationParams['generator_out'],
            baseWorkingDir + "generator_out/",
            cacheType='execution', outputFiles=['*.out'], name='generator_out')

    # *** Sanitizer
    os.mkdir(baseWorkingDir + "sanitizer/")
    # We copy *.in files from generator_in
    for f in glob.glob(baseWorkingDir + "generator_in/*.in"):
        os.symlink(f, baseWorkingDir + "sanitizer/" + os.path.basename(f))
    # We copy *.out files from generator_out
    for f in glob.glob(baseWorkingDir + "generator_out/*.out"):
        os.symlink(f, baseWorkingDir + "sanitizer/" + os.path.basename(f))
    report['sanitizer'] = compileAndRun(evaluationParams['sanitizer'],
            baseWorkingDir + "sanitizer/",
            cacheType='execution', inputFiles=['*.in', '*.out'], name='sanitizer')

    # TODO :: fichiers à récupérer du sanitizer ?

    # *** Checker
    os.mkdir(baseWorkingDir + "checker/")
    report['sanitizer'] = cachedCompile(evaluationParams['checker']['compilationDescr'],
            evaluationParams['checker']['compilationExecution'],
            baseWorkingDir + "checker/",
            getCacheDir(evaluationParams['checker']['compilationDescr']['files'], 'execution')
            'sanitizer')
    
    # TODO :: gestion des erreurs

    # *** Solutions
    os.mkdir(baseWorkingDir + "solutions/")
    solutionsReports = {} # We need this as a dict for later
    solutionsFiles = {} # Source files of solutions, need this for the evaluations
    for sol in evaluationParams['solutions']:
        solDir = "%ssolutions/%s/" % (baseWorkingDir, sol['id'])
        os.mkdir(solDir)
        # We only compile the solution for now
        solReport = cachedCompile(sol['compilationDescr'], sol['compilationExecution'],
               solDir, getCacheDir(sol['compilationDescr']['files'], 'compilation'), 'solution')
        solutionsReports[sol['id']] = solReport
        solutionsFiles[sol['id']] = sol['compilationDescr']['files']

    report['solutions'] = map(lambda k: (k, solutionsReports[k]), solutionsReports.keys())

    # *** Executions
    os.mkdir(baseWorkingDir + "executions/")
    report['executions'] = []
    for test in evaluationParams['executions']:
        testReport = {'name': test['idSolution']} # TODO :: name = ?
        testDir = "%sexecutions/%s.%s/" % (baseWorkingDir, test['idSolution'], test['id'])
        os.mkdir(testDir)

        # We fetch the solution executable
        os.symlink("%ssolutions/%s/solution.exe" % (baseWorkingDir, test['idSolution']), testDir + 'solution.exe')
        # TODO :: fichiers à mettre ?
        # We execute the solution
        testReport['execution'] = cachedExecute(test['runExecution'], testDir + 'solution.exe', testDir,
                getCacheDir(solutionsFiles[test['idSolution']], 'execution'),
                outputFiles=[], compilationReport=solutionsReports[test['idSolution']])
        # We execute the checker
        testReport['checker'] = cachedExecute(evaluationParams['checker']['runExecution'],
                baseWorkingDir + "checker/checker.exe", testDir,
                getCacheDir(evaluationParams['chercker']['compilationDescr']['files'], 'execution'),
                outputFiles=[], compilationReport=report['checker'])
        report['executions'].append((test['id'], testReport)) # TODO :: spec dit "an array of testReport"

    return report


if __name__ == '__main__':
    # TODO :: better interface ?
    if len(sys.argv) == 1:
        print("JSON path missing.")
    else:
        inputJson = json.load(open(sys.argv[1], 'r'))
        outputJson = evaluation(inputJson)
        json.dump(outputJson, open('output.json', 'w'))
