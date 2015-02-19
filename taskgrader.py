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


def getfile(fileDescr, workingDir):
    """Fetch a file contents from a fileDescr object into workingDir.
    If getCache is True, also lookup cache for related cached files."""
    if fileDescr.has_key('content'): # Content given in descr
        open(workingDir + name, 'w').write(fileDescr['content'])
    else: # Get file by path
        os.symlink(repoDir + fileDescr['path'], workingDir + name)
    return None


def getCacheDir(files, cacheType):
    """For a list of source files and the type (compilation or execution),
    returns a tuple containing:
    -whether some related files have been cached
    -where to store/retrieve cache files."""
    fileIdList = []
    fileHashList = []
    for fileDescr in files:
        # We build a list of identifiers for each source file and compute their md5
        if fileDescr.has_key('content'):
            # File content is given, we use the name given as reference
            fileIdList.append("file:%s" % fileDescr['name'])
            fileHashList.append(hashlib.md5(fileDescr['content']).hexdigest())
        else:
            # File path is given, we use the path as reference
            fileIdList.append("path:%s" % fileDescr['path'])
            fileHashList.append(hashlib.md5(open(CFG_CACHEDIR + fileDescr['path'], 'rb').read()).hexdigest())

    fileIdList.sort()
    fileHashList.sort() # Both lists won't be sorted the same but it's not an issue
    # This will be the ID string in the database, containing the cache type and the source files list
    filesId = "cache:%s;%s" % (cacheType, ";".join(fileIdList))

    # TODO :: vraie DB quand le program sera complet
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
            for f in os.listDir("%s%s/" % (CFG_CACHEDIR, dbId)):
                os.remove("%s%s/%s" % (CFG_CACHEDIR, dbId, f))
            return (False, "%s%s/" % (CFG_CACHEDIR, dbId))
    else:
        # New entry in database
        newId = len(database)
        database[filesId] = (newId, fileHashList)
        os.mkdir("%s%s/" % (CFG_CACHEDIR, newId))
        return (False, "%s%s/" % (CFG_CACHEDIR, newId))


def capture(fd, name='', truncateSize=-1):
    """Capture a file descriptor contents for inclusion into the output json."""
    report = {'name': name,
              'sizeKb': os.path.getsize(workingDir + name) / 1024}
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
    executionReport['stdout'] = capture(open('stdout.out', 'r'),
            name='stdout',
            truncateSize=executionParams['stdoutTruncateKb'] * 1024)
    executionReport['stderr'] = capture(open('stderr.out', 'r'),
            name='stderr',
            truncateSize=executionParams['stderrTruncateKb'] * 1024)
    filesReports = []
    for globf in executionParams['getFiles']:
        for f in glob.glob(workingDir + globf):
            filesReports.append(capture(open(f, 'r'), name=os.path.basename(f)))
            # TODO :: truncateSize manquant dans la spec ?
    executionReport['files'] = filesReports


def compile(compilationDescr, executionParams, workingDir, name='executable'):
    """Compile a program."""
    for source in compilationDescr['files']: # Fetch source files
        getFile(f, workingDir)
    for dep in compilationDescr['dependencies']: # Fetch dependencies
        getFile(dep, workingDir)
    # TODO :: compilation
    pass


def compileAndRun(compileAndRunParams, workingDir, cache=None, outputFiles=[], name='executable'):
    """Compile a program and then run it.
    cache argument tells what we should cache (or fetch from cache), either
    the compiled executable or the output of the executable.
    outputFiles tells which files are considered as output of the run and
    should thus be cached."""
    report = {}
    if cache == None:
        # We compile and run without any cache
        report['compilationExecution'] = compile(compileAndRunParams['compilationDescr'],
                                             compileAndRunParams['compilationExecution'],
                                             workingDir,
                                             name)
        report['runExecution'] = execute('%s%s.exe' % (workingDir, name), compileAndRunParams['runExecution'], workingDir)
    else:
        # We fetch the cache status
        # TODO :: rajouter les fichiers d'input dans la liste des fichiers
        (cacheStatus, cacheDir) = getCacheDir(compileAndRunParams['compilationDescr']['files'], cache)
        if cacheStatus:
            if cache == 'compilation':
                # We load the report and the executable from cache
                report['compilationExecution'] = json.load(open("%scompilationExecution.json" % cacheDir, 'r'))
                os.symlink("%s%s.exe" % (cacheDir, name), "%s%s.exe" % (workingDir, name))

                report['runExecution'] = execute("%s%s.exe" % (workingDir, name), compileAndRunParams['runExecution'], workingDir)
            elif cache == 'execution':
                # We load both execution reports and results from cache
                report['compilationExecution'] = json.load(open("%scompilationExecution.json" % cacheDir, 'r'))
                report['runExecution'] = json.load(open("%srunExecution.json" % cacheDir, 'r'))
                # We load cached files (as symlinks)
                for g in outputFiles:
                    for f in glob.glob(cacheDir + g):
                        os.symlink(f, workingDir + os.path.basename(f))
        else:
            # No current cache, we'll have to cache the results
            report['compilationExecution'] = compile(compileAndRunParams['compilationDescr'],
                    compileAndRunParams['compilationExecution'],
                    workingDir, name)
            report['runExecution'] = execute('%s%s.exe' % (workingDir, name), compileAndRunParams['runExecution'], workingDir)
            if cache == 'compilation':
                # We only cache the compiled executable and the related report
                shutil.copy("%s%s.exe" % (workingDir, name), cacheDir)
                json.dump(report['compilationExecution'], open("%scompilationExecution.json" % cacheDir, 'r'))
            elif cache == 'execution':
                # We copy results into cache
                for g in outputFiles:
                    for f in glob.glob(cacheDir + g):
                        shutil.copy(f, workingDir)
                # We copy both reports in cache
                json.dump(report['compilationExecution'], open("%scompilationExecution.json" % cacheDir, 'r'))
                json.dump(report['runExecution'], open("%srunExecution.json" % cacheDir, 'r'))

    return report


def evaluation(evaluationParams):
    baseWorkingDir = evaluationParams['rootPath'] + evaluationParams['output_path']
    os.mkdir(baseWorkingDir)

    # Generator_in
    os.mkdir(baseWorkingDir + "generator_in/")
    compileAndRun(evaluationParams['generator_in'], baseWorkingDir + "generator_in/",
            cache='execution', outputFiles=['*.in'], name='generator_in')

    # TODO :: ajouter fichiers in supplémentaires (spec ?)

    # Generator_out
    os.mkdir(baseWorkingDir + "generator_out/")
    # We copy *.in files from generator_in
    for f in glob.glob(baseWorkingDir + "generator_in/*.in"):
        os.symlink(f, baseWorkingDir + "generator_out/" + os.path.basename(f))
    compileAndRun(evaluationParams['generator_out'], baseWorkingDir + "generator_out/",
            cache='execution', outputFiles=['*.out'], name='generator_out')

    # Sanitizer
    os.mkdir(baseWorkingDir + "sanitizer/")
    # We copy *.in files from generator_in
    for f in glob.glob(baseWorkingDir + "generator_in/*.in"):
        os.symlink(f, baseWorkingDir + "sanitizer/" + os.path.basename(f))
    # We copy *.out files from generator_out
    for f in glob.glob(baseWorkingDir + "generator_out/*.out"):
        os.symlink(f, baseWorkingDir + "sanitizer/" + os.path.basename(f))
    compileAndRun(evaluationParams['sanitizer'], baseWorkingDir + "sanitizer/",
            cache='execution', outputFiles=['*.in', '*.out'], name='sanitizer')

    # TODO :: checker

    # TODO :: gestion des erreurs

    # Solutions
    for sol in evaluationParams['solutions']:
        # TODO :: solutions
        # tenter de compiler
        # effectuer chacun des tests
