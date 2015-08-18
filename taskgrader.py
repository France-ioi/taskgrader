#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This simple tool manages every step of grading a contest task, from the
# generation of test data to the grading of a solution output.
# See README.md for more information.


import glob, hashlib, json, os, random, shlex, shutil, sqlite3, sys, subprocess
from config import *

sys.path.append(CFG_JSONSCHEMA)
from jsonschema import validate


def preprocessJson(json, varData):
    """Preprocess some JSON data, replacing variables with their values.
    There's no checking of the type of values in the variables; the resulting
    JSON is supposed to be checked against a JSON schema.
    varData represents the variable data; all values written as '@varname' in
    the JSON will be replaced by varData['varname']."""
    if (type(json) is str or type(json) is unicode) and len(json) > 0:
        if json[0] == '@':
            # It's a variable, we replace it with the JSON data
            varName = json[1:]
            if varData.has_key(varName):
                return preprocessJson(varData[varName], varData)
            else:
                raise Exception("varData doesn't have key `%s`, contents of varData:\n%s" % (varName, str(varData)))
        elif '$' in json:
            if '$BUILD_PATH' in json:
                return preprocessJson(json.replace('$BUILD_PATH', varData['BUILD_PATH']), varData)
            elif '$ROOT_PATH' in json:
                return preprocessJson(json.replace('$ROOT_PATH', varData['ROOT_PATH']), varData)
            elif '$TASK_PATH' in json:
                return preprocessJson(json.replace('$TASK_PATH', varData['TASK_PATH']), varData)
            else:
                return json
        else:
            return json
    elif type(json) is dict:
        # It's a dict, we process the values in it
        newjson = {}
        for k in json.keys():
            newjson[k] = preprocessJson(json[k], varData)
        return newjson
    elif type(json) is list:
        # It's a list, we filter the values in it
        newjson = map(lambda x: preprocessJson(x, varData), json)
        # We remove None values, which are probably undefined variables
        while None in newjson:
            newjson.remove(None)
        return newjson
    else:
        return json


def isInRestrict(path):
    """Check whether a path is in the allowed paths for read/write."""
    global restrictToPaths
    if len(restrictToPaths) == 0:
        return True
    for folder in restrictToPaths:
        if os.path.abspath(path).startswith(os.path.abspath(folder) + '/'):
            return True
    return False


def symlink(filefrom, fileto, fromlocal=False, tolocal=False):
    """Make a symlink. *local variables indicate whether the paths must be
    explicitly allowed or not."""
    if fromlocal and not isInRestrict(filefrom):
        raise Exception("Loading file `%s` not allowed." % filefrom)
    if tolocal and not isInRestrict(fileto):
        raise Exception("Loading file `%s` not allowed." % fileto)
    os.symlink(filefrom, fileto)

def filecopy(filefrom, fileto, fromlocal=False, tolocal=False):
    """Copy a file. *local variables indicate whether the paths must be
    explicitly allowed or not."""
    if fromlocal and not isInRestrict(filefrom):
        raise Exception("Loading file `%s` not allowed." % filefrom)
    if tolocal and not isInRestrict(fileto):
        raise Exception("Loading file `%s` not allowed." % fileto)
    shutil.copy(filefrom, fileto)


def isExecError(executionReport):
    """Returns whether an execution returned an error according to its exit code."""
    return (executionReport['exitCode'] != 0)


def getFile(fileDescr, workingDir, buildDir=None, language=''):
    """Fetch a file contents from a fileDescr object into workingDir.
    If only the file name is given, getFile will search for a file with that
    name in buildDir. If language is defined, it will search for a file
    related to that language first."""

    if '../' in fileDescr['name']:
        raise Exception("File name `%s` is invalid." % fileDescr['name'])

    if os.path.isfile(workingDir + fileDescr['name']):
        # File already exists
        raise Exception("File %s already exists in %s" % (fileDescr['name'], workingDir))

    if '/' in fileDescr['name']:
        # Need to make a folder
        try:
            os.makedirs(workingDir + '/'.join(fileDescr['name'].split('/')[:-1]))
        except:
            pass
        

    if fileDescr.has_key('content'): # Content given in descr
        open(workingDir + fileDescr['name'], 'w').write(fileDescr['content'].encode('utf-8'))
    elif fileDescr.has_key('path'): # Get file by path
        if os.path.isfile(fileDescr['path']):
            symlink(fileDescr['path'], workingDir + fileDescr['name'], fromlocal=True)
        else:
            raise Exception("File not found: %s" % fileDescr['path'])
    else: # File is a built dependency
        if not buildDir:
            buildDir = workingDir
        if os.path.isfile('%slibs/%s-%s' % (buildDir, language, fileDescr['name'])):
            # We search for [language]-[name] in the libs directory
            symlink('%slibs/%s-%s' % (buildDir, language, fileDescr['name']), workingDir + fileDescr['name'])
        elif language == 'cpp' and os.path.isfile('%slibs/c-%s' % (buildDir, fileDescr['name'])):
            # For cpp, we also search for c-[name] in the libs directory
            symlink('%slibs/c-%s' % (buildDir, fileDescr['name']), workingDir + fileDescr['name'])
        elif language in ['python', 'python2', 'python3'] and os.path.isfile('%slibs/run-%s' % (buildDir, fileDescr['name'])):
            # For Python languages, we search for run-[name] in the libs directory
            symlink('%slibs/run-%s' % (buildDir, fileDescr['name']), workingDir + fileDescr['name'])
        elif os.path.isfile('%slibs/%s' % (buildDir, fileDescr['name'])):
            # We search for [name] in the libs directory
            symlink('%slibs/%s' % (buildDir, fileDescr['name']), workingDir + fileDescr['name'])
        else:
            raise Exception("Dependency not found: %s for language %s" % (fileDescr['name'], language))
    return None


def getCacheDir(files, cacheType, inputFiles=[]):
    """For a list of source files and the type (compilation or execution),
    returns a tuple containing:
    -whether some related files have been cached
    -the folder containing cache files.
    It hits the cache when the file list and corresponding MD5 hashes are
    the same; it uses a SQLite3 database to store the information.
    Cache will consist of folders, each folder named after the ID in the
    database and containing all the cached files."""

    fileIdList = []
    fileHashList = []
    # We build a list of identifiers for each source file and compute their md5
    for fileDescr in files:
        if fileDescr.has_key('content'):
            # File content is given, we use the name given and the hash as reference
            md5sum = hashlib.md5(fileDescr['content'].encode('utf-8', errors='ignore')).hexdigest()
            fileIdList.append("file:%s:%s" % (fileDescr['name'], md5sum))
            fileHashList.append(md5sum)
        else:
            # File path is given, we use the path as reference
            fileIdList.append("path:%s" % fileDescr['path'])
            fileHashList.append(hashlib.md5(open(fileDescr['path'], 'rb').read()).hexdigest())

    # We add identifiers for input files (local name and md5sum)
    for f in inputFiles:
        md5sum = hashlib.md5(open(f, 'rb').read()).hexdigest()
        fileIdList.append("input:%s:%s" % (os.path.basename(f), md5sum))

    fileIdList.sort()
    fileHashList.sort() # Both lists won't be sorted the same but it's not an issue

    # We make a text version for the database
    fileHashes = ';'.join(fileHashList)
    # This will be the ID string in the database, containing the cache type and the source files list
    filesId = "cache:%s;%s" % (cacheType, ";".join(fileIdList))

    # Read cache information from database
    dbCur = CFG_CACHEDB.cursor()
    dbCur.execute("SELECT * FROM cache WHERE filesId=?", [filesId])
    dbRow = dbCur.fetchone()
    if dbRow:
        # This list of files already exists in the database
        dbId = dbRow['id']
        dbHashes = dbRow['hashlist']
        if dbHashes == fileHashes and os.path.isfile("%s%s/cache.ok" % (CFG_CACHEDIR, dbId)):
            # MD5 hashes are good
            return (True, "%s%s/" % (CFG_CACHEDIR, dbId))
        else:
            # MD5 hashes changed, update database, invalidate cache
            dbCur.execute("UPDATE cache SET hashlist=? WHERE filesid=?", [fileHashes, filesId])
            CFG_CACHEDB.commit()
            try:
                shutil.rmtree("%s%s" % (CFG_CACHEDIR, dbId))
            except:
                pass
            os.mkdir("%s%s/" % (CFG_CACHEDIR, dbId))
            return (False, "%s%s/" % (CFG_CACHEDIR, dbId))
    else:
        # New entry in database
        dbCur.execute("INSERT INTO cache(filesid, hashlist) VALUES(?, ?)", [filesId, fileHashes])
        CFG_CACHEDB.commit()
        newId = dbCur.lastrowid
        os.mkdir("%s%s/" % (CFG_CACHEDIR, newId))
        return (False, "%s%s/" % (CFG_CACHEDIR, newId))


def capture(path, name='', truncateSize=-1):
    """Capture a file contents for inclusion into the output JSON as a
    captureReport object."""
    if not isInRestrict(path):
        raise Exception("Opening file `%s` is not allowed.")
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


def execute(executionParams, cmdLine, workingDir, stdinFile=None, stdoutFile=None, language='', isolate=True):
    """Execute a command line and build the report.
    Executes the command line cmdLine according to the parameters from
    executionParams, in directory workingDir.
    If isolate is True, it will run the program in a sandbox.
    stdinFile and stdoutFile allows to control input/output of the program,
    and language allows to know whether use some mem/time transformation
    functions as defined in config.py ."""

    # Check time and memory limits
    if executionParams['timeLimitMs'] > CFG_MAX_TIMELIMIT:
        raise Exception("Time limit (%d) for command %s too high." % (executionParams['timeLimitMs'], cmdLine))
    if executionParams['memoryLimitKb'] > CFG_MAX_MEMORYLIMIT:
        raise Exception("Memory limit (%d) for command %s too high." % (executionParams['memoryLimitKb'], cmdLine))

    # Values copied from the arguments
    report = {'timeLimitMs': executionParams['timeLimitMs'],
            'memoryLimitKb': executionParams['memoryLimitKb'],
            'commandLine': cmdLine,
            'wasCached': False}

    # Transformation of time and memory limits for the language
    realMemoryLimitKb = CFG_TRANSFORM_MEM.get(language, CFG_TRANSFORM_MEM_DEFAULT)(executionParams['memoryLimitKb'])
    report['realMemoryLimitKb'] = realMemoryLimitKb

    (timeTransform, timeUntransform) = CFG_TRANSFORM_TIME.get(language, CFG_TRANSFORM_TIME_DEFAULT)
    realTimeLimit = timeTransform(executionParams['timeLimitMs'])
    report['realTimeLimitMs'] = realTimeLimit

    if stdoutFile == None:
        stdoutFile = workingDir + 'stdout'
    elif not isInRestrict(stdoutFile):
        raise Exception("Writing to file `%s` not allowed." % stdoutFile)

    if isolate:
        # Box ID is required if multiple isolate instances are running concurrently
        boxId = (os.getpid() % 100)

        isolateCommonOpts = ['--box-id=%d' % boxId]
        if CFG_CONTROLGROUPS:
            isolateCommonOpts.append('--cg')

        # Initialize isolate box
        initProc = subprocess.Popen([CFG_ISOLATEBIN, '--init'] + isolateCommonOpts, stdout=subprocess.PIPE, cwd=workingDir)
        (isolateDir, isolateErr) = initProc.communicate()
        initProc.wait()
        # isolatePath will be the path of the sandbox, as given by isolate
        isolateDir = isolateDir.strip() + '/box/'

        # Build isolate command line
        isolatedCmdLine  = CFG_ISOLATEBIN
        isolatedCmdLine += ' --processes'
        isolatedCmdLine += ' --env=HOME --env=PATH'
        isolatedCmdLine += ' --meta=' + workingDir + 'isolate.meta'
        # Use an unique box ID
        isolatedCmdLine += ' --box-id=%d' % boxId
        if executionParams['timeLimitMs'] > 0:
            isolatedCmdLine += ' --time=' + str(realTimeLimit / 1000.)
        if executionParams['memoryLimitKb'] > 0:
            if CFG_CONTROLGROUPS:
                isolatedCmdLine += ' --cg-mem=' + str(realMemoryLimitKb)
            else:
                isolatedCmdLine += ' --mem=' + str(realMemoryLimitKb)
        if stdinFile:
            if os.path.isfile(stdinFile):
                filecopy(stdinFile, isolateDir + 'isolated.stdin', fromlocal=True)
                isolatedCmdLine += ' --stdin=isolated.stdin'
            else:
                raise Exception("Input file %s not found while preparing to execute command %s." % (stdinFile, cmdLine))
        if CFG_CONTROLGROUPS:
            isolatedCmdLine += ' --cg --cg-timing'
        isolatedCmdLine += ' --stdout=isolated.stdout --stderr=isolated.stderr'
        isolatedCmdLine += ' --run -- ' + cmdLine

        # Copy files from working directory to sandbox
        for f in os.listdir(workingDir):
            filecopy(workingDir + f, isolateDir + f)

        open(workingDir + 'isolate.meta', 'w')

        # Execute the isolated program
        proc = subprocess.Popen(shlex.split(isolatedCmdLine), cwd=workingDir)
        proc.wait()

        # Set file rights so that we can access the files
        rightsProc = subprocess.Popen([CFG_RIGHTSBIN])
        rightsProc.wait()

        # Copy back the files from sandbox
        for f in os.listdir(isolateDir):
            if os.path.isfile(isolateDir + f):
                filecopy(isolateDir + f, workingDir + f)
        filecopy(isolateDir + 'isolated.stdout', stdoutFile)

        # Get metadata from isolate execution
        isolateMeta = {}
        for l in open(workingDir + 'isolate.meta', 'r').readlines():
            [name, val] = l.split(':', 1)
            isolateMeta[name] = val.strip()

        # Generate execution report
        if isolateMeta.has_key('time'):
            report['realTimeTakenMs'] = int(float(isolateMeta['time'])*1000)
            report['timeTakenMs'] = int(timeUntransform(report['realTimeTakenMs']))
        else:
            report['realTimeTakenMs'] = -1
            report['timeTakenMs'] = -1
        # Memory used: cg-mem is only available when control groups are
        # enabled, and max-rss can be slightly inaccurate
        if isolateMeta.has_key('cg-mem'):
            report['memoryUsedKb'] = int(isolateMeta['cg-mem'])
        elif isolateMeta.has_key('max-rss'):
            report['memoryUsedKb'] = int(isolateMeta['max-rss'])
        else:
            report['memoryUsedKb'] = -1
        report['wasKilled'] = isolateMeta.has_key('killed')
        report['exitCode'] = int(isolateMeta.get('exitcode', proc.returncode))

        report['stdout'] = capture(workingDir + 'isolated.stdout', name='stdout',
                truncateSize=executionParams['stdoutTruncateKb'] * 1024)
        report['stderr'] = capture(workingDir + 'isolated.stderr', name='stderr',
                truncateSize=executionParams['stderrTruncateKb'] * 1024)

        # Cleanup sandbox
        cleanProc = subprocess.Popen([CFG_ISOLATEBIN, '--cleanup'] + isolateCommonOpts, cwd=workingDir)
        cleanProc.wait()
    else:
        # We don't use isolate
        if stdinFile:
            if os.path.isfile(stdinFile) and isInRestrict(stdinFile):
                stdinHandle = open(stdinFile, 'rb')  
            else:
                raise Exception("Input file %s not found while preparing to execute command %s." % (stdinFile, cmdLine))
        else:
            stdinHandle = None
        proc = subprocess.Popen(shlex.split(cmdLine), stdin=stdinHandle, stdout=open(stdoutFile, 'w'),
                stderr=open(workingDir + 'stderr', 'w'), cwd=workingDir)

        proc.wait()

        # Generate execution report
        report['timeTakenMs'] = -1 # We don't know
        report['realTimeTakenMs'] = -1 # We don't know
        report['wasKilled'] = False
        report['exitCode'] = proc.returncode

        report['stdout'] = capture(stdoutFile, name='stdout',
                truncateSize=executionParams['stdoutTruncateKb'] * 1024)
        report['stderr'] = capture(workingDir + 'stderr', name='stderr',
                truncateSize=executionParams['stderrTruncateKb'] * 1024)

    filesReports = []
    for globf in executionParams['getFiles']:
        for f in glob.glob(workingDir + globf):
            filesReports.append(capture(f, name=os.path.basename(f), truncateSize=CFG_MAX_GETFILE))
    report['files'] = filesReports

    return report


def cachedExecute(executionParams, cmdLine, workingDir, cacheData, stdinFile=None, stdoutFile=None, outputFiles=[], language=''):
    """Get the results from execution of a program, either by fetching them
    from cache, or by actually executing the program.
    cachedExecute will look at the cacheData (fetched with the function
    getCacheDir) and determine whether to fetch files from cache, whether to
    pass the arguments to the function execute. In that case, it will cache the results after the execution."""
    if executionParams['useCache']:
        (cacheStatus, cacheDir) = cacheData
        if cacheStatus:
            # Results are in cache, we fetch the report
            report = json.load(open("%srunExecution.json" % cacheDir, 'r'))
            report['wasCached'] = True
            # We load cached results (as symlinks)
            for g in outputFiles:
                for f in glob.glob(cacheDir + g):
                    symlink(f, workingDir + os.path.basename(f))
        else:
            # We execute again the program
            report = execute(executionParams, cmdLine, workingDir, stdinFile=stdinFile, stdoutFile=stdoutFile, language=language)
            # We save results to cache
            for g in outputFiles:
                for f in glob.glob(workingDir + g):
                    filecopy(f, cacheDir)
            json.dump(report, open("%srunExecution.json" % cacheDir, 'w'))
            open("%scache.ok" % cacheDir, 'w')
    else:
        # We don't use cache at all
        report = execute(executionParams, cmdLine, workingDir, stdinFile=stdinFile, stdoutFile=stdoutFile, language=language)

    return report


def compile(compilationDescr, executionParams, workingDir, buildDir='./', name='executable'):
    """Effectively compile a program, not using cache (probably because
    there's no cached version).
    It fetches the files as described by the compilationDescr, and uses the
    executionParams as parameters for the compiler execution.
    The resulting file will by named '[name].exe'."""
    # We fetch source files into the workingDir
    sourceFiles = []
    for source in compilationDescr['files']: # Fetch source files
        getFile(source, workingDir)
        sourceFiles.append(source['name'])

    # We fetch dependencies into the workingDir
    depFiles = []
    for dep in compilationDescr['dependencies']: # Fetch dependencies
        getFile(dep, workingDir, buildDir=buildDir, language=compilationDescr['language'])
        depFiles.append(dep['name'])

    # We compile according to the source type
    if compilationDescr['language'] == 'c':
        cmdLine = "/usr/bin/gcc -static -std=gnu99 -O2 -Wall -o %s.exe %s -lm" % (name, ' '.join(sourceFiles))
        report = execute(executionParams, cmdLine, workingDir, isolate=False)
    elif compilationDescr['language'] == 'cpp':
        cmdLine = "/usr/bin/g++ -static -O2 -Wall -o %s.exe %s -lm" % (name, ' '.join(sourceFiles))
        report = execute(executionParams, cmdLine, workingDir, isolate=False)
    elif compilationDescr['language'] == 'cpp11':
        cmdLine = "/usr/bin/g++ -std=gnu++11 -static -O2 -Wall -o %s.exe %s -lm" % (name, ' '.join(sourceFiles))
        report = execute(executionParams, cmdLine, workingDir, isolate=False)
    elif compilationDescr['language'] == 'ocaml':
        cmdLine = "/usr/bin/ocamlopt -ccopt -static -o %s.exe %s" % (name, ' '.join(sourceFiles))
        report = execute(executionParams, cmdLine, workingDir, isolate=False)
    elif compilationDescr['language'] == 'pascal':
        cmdLine = "/usr/bin/fpc -o%s.exe %s" % (name, ' '.join(sourceFiles))
        report = execute(executionParams, cmdLine, workingDir, isolate=False)
    elif compilationDescr['language'] == 'java':
        cmdLine = "/usr/bin/gcj --encoding=utf8 --main=Main -o %s.exe %s" % (name, ' '.join(sourceFiles))
        report = execute(executionParams, cmdLine, workingDir, isolate=False)
    elif compilationDescr['language'] == 'javascool':
        # Javascool needs to be transformed before being executed
        cmdLine = "%s %s source.java %s" % (CFG_JAVASCOOLBIN, sourceFiles[0], ' '.join(depFiles))
        execute(executionParams, cmdLine, workingDir, isolate=False)
        cmdLine = "/usr/bin/gcj --encoding=utf8 --main=Main -o %s.exe source.java" % name
        report = execute(executionParams, cmdLine, workingDir, isolate=False)
    # TODO :: compilation de PHP5
    elif compilationDescr['language'] in ['shell', 'python', 'python2', 'python3']:
        # Scripts are not "compiled", we make an archive out of the source files
        # shar makes a self-extracting "shell archive"
        sharFile = open(workingDir + name + '.exe', 'w+')
        subprocess.Popen(['shar', '--quiet-unshar', '--quiet'] + sourceFiles + depFiles, stdout=sharFile, cwd=workingDir).wait()
        # We remove the last line of the archive (normally an 'exit 0')
        sharFile.seek(-5, os.SEEK_END)
        pos = sharFile.tell()
        while pos > 0 and sharFile.read(1) != "\n":
            pos -=1
            sharFile.seek(pos, os.SEEK_SET)
        if pos > 0:
            sharFile.truncate(pos + 1)
        # We set the archive to execute the script(s) after self-extracting
        if compilationDescr['language'] == 'shell':
            sharFile.write("export TASKGRADER_DEPFILES=\"%s\"\n" % ' '.join(depFiles))
            sharFile.writelines(map(lambda x: "/bin/sh %s $@\n" % x, sourceFiles))
        elif compilationDescr['language'] == 'python2':
            sharFile.write("/usr/bin/python2 %s $@" % ' '.join(sourceFiles))
        elif compilationDescr['language'] == 'python3' or compilationDescr['language'] == 'python':
            sharFile.write("/usr/bin/python3 %s $@" % ' '.join(sourceFiles))
        # On some versions, shar ignores the --quiet-unshar option and talks too much
        # We replace echo= statements with echo=true as a dirty fix
        sharFile.seek(0)
        sharLines = []
        for l in sharFile:
            sharLines.append(l.replace('echo=echo', 'echo=true').replace('echo="$gettext_dir/gettext -s"', 'echo=true'))
        sharFile.seek(0)
        sharFile.truncate(0)
        sharFile.writelines(sharLines)
        sharFile.close()
        # We set the archive executable bits
        os.chmod(workingDir + name + '.exe', 493) # chmod 755
        # We build a dummy report
        report = {'timeLimitMs': executionParams['timeLimitMs'],
                'memoryLimitKb': executionParams['memoryLimitKb'],
                'commandLine': '[shell script built]',
                'timeTakenMs': 0,
                'realTimeTakenMs': 0,
                'wasKilled': False,
                'wasCached': False,
                'exitCode': 0}
    else:
        report = {'errorcode': 2, 'errormsg': 'unknown language: %s' % compilationDescr['language']}
    return report


def cachedCompile(compilationDescr, executionParams, workingDir, cacheData, buildDir='./', name='executable'):
    """Get the compiled version of a program, either by fetching it from cache
    if possible, either by compiling it."""
    if executionParams['useCache']:
        (cacheStatus, cacheDir) = cacheData
        if cacheStatus:
            # We load the report and executable from cache
            symlink("%s%s.exe" % (cacheDir, name), "%s%s.exe" % (workingDir, name))
            report = json.load(open("%scompilationExecution.json" % cacheDir, 'r'))
            report['wasCached'] = True
        else:
            # No current cache, we compile
            report = compile(compilationDescr, executionParams, workingDir, buildDir=buildDir, name=name)
            # We cache the results
            filecopy("%s%s.exe" % (workingDir, name), cacheDir)
            json.dump(report, open("%scompilationExecution.json" % cacheDir, 'w'))
            open("%scache.ok" % cacheDir, 'w')
    else:
        # We don't use cache at all
        report = compile(compilationDescr, compilationExecution, workingDir, buildDir=buildDir, name=name)

    return report


def evaluation(evaluationParams):
    """Full evaluation process."""

    global restrictToPaths

    # *** Variables handling
    varData = {'ROOT_PATH': evaluationParams['rootPath'],
               'TASK_PATH': evaluationParams['taskPath']}

    # Load path restriction is present
    if evaluationParams.has_key('restrictToPaths'):
        restrictToPaths = evaluationParams['restrictToPaths']
    else:
        restrictToPaths = []

    # We load a "preprocessing" JSON node or file
    try:
        varData.update(json.load(open(os.path.join(evaluationParams['taskPath'].replace('$ROOT_PATH', evaluationParams['rootPath']), 'defaultParams.json'), 'r')))
    except:
        pass
    if evaluationParams.has_key('extraParams'):
        if type(evaluationParams['extraParams']) is str and isInRestrict(evaluationParams['extraParams']):
            varData.update(json.load(open(evaluationParams['extraParams'], 'r')))
        else:
            varData.update(evaluationParams['extraParams'])
    evaluationParams = preprocessJson(evaluationParams, varData)

    # Path where the evaluation will take place
    if evaluationParams.has_key('outputPath'):
        if '../' in evaluationParams['outputPath']:
            raise Exception("Output path `%s` invalid." % evaluationParams['outputPath'])
        baseWorkingDir = CFG_BUILDSDIR + evaluationParams['outputPath']
    else:
        baseWorkingDir = CFG_BUILDSDIR + '_build' + str(random.randint(0, 10000)) + '/'
        while os.path.isdir(baseWorkingDir):
            baseWorkingDir = CFG_BUILDSDIR + '_build' + str(random.randint(0, 10000)) + '/'
    os.mkdir(baseWorkingDir)

    report = {}

    varData['BUILD_PATH'] = baseWorkingDir
    report['buildPath'] = baseWorkingDir
    if len(restrictToPaths) > 0:
        restrictToPaths.append(baseWorkingDir)

    # We validate the input JSON format
    try:
        validate(evaluationParams, json.load(open(CFG_INPUTSCHEMA, 'r')))
    except Exception as err:
        raise Exception("Validation failed for input JSON, error message: %s" % str(err))

    os.mkdir(baseWorkingDir + "libs/")
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
               genDir, getCacheDir(gen['compilationDescr']['files'] + gen['compilationDescr']['dependencies'], 'c-generator'), baseWorkingDir, 'generator')
        errorSoFar = errorSoFar or isExecError(genReport)
        report['generators'].append({'id': gen['id'], 'compilationExecution': genReport})
        generatorsFiles[gen['id']] = gen['compilationDescr']['files'] + gen['compilationDescr']['dependencies']


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
                    filecopy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idGenerator'], genDir + 'generator.exe', fromlocal=True)
                    genReport['generatorExecution'] = cachedExecute(gen['genExecution'], "generator.exe %s" % tc['params'], genDir,
                            getCacheDir(generatorsFiles[gen['idGenerator']], 'e-generator:' + tc['params']),
                            stdoutFile=genDir + tc['name'] + '.in',
                            outputFiles=[tc['name'] + '.in'])
                    if not isExecError(genReport['generatorExecution']):
                        filecopy(genDir + tc['name'] + '.in', baseWorkingDir + 'tests/' + tc['name'] + '.in')

                    filecopy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idOutputGenerator'], genDir + 'outgenerator.exe', fromlocal=True)
                    genReport['outputGeneratorExecution'] = cachedExecute(gen['outGenExecution'], "outgenerator.exe %s" % tc['params'], genDir,
                            getCacheDir(generatorsFiles[gen['idOutputGenerator']], 'e-generator:' + tc['params']),
                            stdoutFile=genDir + tc['name'] + '.out',
                            outputFiles=[tc['name'] + '.out'])
                    if not isExecError(genReport['outputGeneratorExecution']):
                        filecopy(genDir + tc['name'] + '.out', baseWorkingDir + 'tests/' + tc['name'] + '.out', fromlocal=True, tolocal=True)
                    errorSoFar = errorSoFar or isExecError(genReport['generatorExecution']) or isExecError(genReport['outputGeneratorExecution'])
                else:
                    # We only have one generator, we assume `name` is the name of the test file to generate
                    filecopy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idGenerator'], genDir + 'generator.exe', fromlocal=True)
                    genReport['generatorExecution'] = cachedExecute(gen['genExecution'], "generator.exe %s" % tc['params'], genDir,
                            getCacheDir(generatorsFiles[gen['idGenerator']], 'e-generator:' + tc['params']),
                            stdoutFile=genDir + tc['name'],
                            outputFiles=[tc['name']])
                    if isExecError(genReport['generatorExecution']):
                        errorSoFar = True
                    else:
                        filecopy(genDir + tc['name'], baseWorkingDir + 'tests/' + tc['name'], fromlocal=True, tolocal=True)
                report['generations'].append(genReport)
                
        else:
            # We generate the test cases just by executing the generators
            genReport = {'id': gen['id']}
            filecopy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idGenerator'], genDir + 'generator.exe', fromlocal=True)
            genReport['generatorExecution'] = cachedExecute(gen['genExecution'], "generator.exe", genDir,
                    getCacheDir(generatorsFiles[gen['idGenerator']], 'e-generator'), outputFiles=['*.in', '*.out', '*.h', '*.java', '*.ml', '*.mli', '*.pas', '*.py'])
            errorSoFar = errorSoFar or isExecError(genReport['generatorExecution'])
            if gen.has_key('idOutputGenerator'):
                # We also have an output generator
                filecopy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idOutputGenerator'], genDir + 'outgenerator.exe', fromlocal=True)
                genReport['outputGeneratorExecution'] = cachedExecute(gen['outGenExecution'], "outgenerator.exe" % gen['idOutputGenerator'], genDir,
                        getCacheDir(generatorsFiles[gen['idOutputGenerator']], 'e-generator'), outputFiles=['*.out'])
                errorSoFar = errorSoFar or isExecError(genReport['outputGeneratorExecution'])
            report['generations'].append(genReport)
            # We copy the generated test files
            for f in (glob.glob(genDir + '*.in') + glob.glob(genDir + '*.out')):
                filecopy(f, baseWorkingDir + 'tests/')
            # We copy the generated lib files
            libFiles = []
            for ext in ['*.h', '*.java', '*.ml', '*.mli', '*.pas', '*.py']:
                libFiles.extend(glob.glob(genDir + ext))
            for f in libFiles:
                filecopy(f, baseWorkingDir + 'libs/')

    # We add extra tests
    if evaluationParams.has_key('extraTests'):
        for et in evaluationParams['extraTests']:
            getFile(et, baseWorkingDir + "tests/")

    # *** Sanitizer
    os.mkdir(baseWorkingDir + "sanitizer/")
    report['sanitizer'] = cachedCompile(evaluationParams['sanitizer']['compilationDescr'],
            evaluationParams['sanitizer']['compilationExecution'],
            baseWorkingDir + "sanitizer/",
            getCacheDir(evaluationParams['sanitizer']['compilationDescr']['files'] + evaluationParams['sanitizer']['compilationDescr']['dependencies'], 'c-sanitizer'),
            baseWorkingDir, 'sanitizer')
    errorSoFar = errorSoFar or isExecError(report['sanitizer'])

    # *** Checker
    os.mkdir(baseWorkingDir + "checker/")
    report['checker'] = cachedCompile(evaluationParams['checker']['compilationDescr'],
            evaluationParams['checker']['compilationExecution'],
            baseWorkingDir + "checker/",
            getCacheDir(evaluationParams['checker']['compilationDescr']['files'] + evaluationParams['sanitizer']['compilationDescr']['dependencies'], 'c-checker'),
            baseWorkingDir, 'checker')
    errorSoFar = errorSoFar or isExecError(report['sanitizer'])


    # Did we encounter an error so far?
    if errorSoFar:
        raise Exception("Error in task generation. Please check the partial report for more information:\n%s" % json.dumps(report))


    # *** Solutions
    os.mkdir(baseWorkingDir + "solutions/")
    report['solutions'] = []
    solutionsInfo = {} # Language and source files of solutions, need this for the evaluations
    solutionsWithErrors = []
    for sol in evaluationParams['solutions']:
        solDir = "%ssolutions/%s/" % (baseWorkingDir, sol['id'])
        os.mkdir(solDir)
        # We only compile the solution
        solReport = cachedCompile(sol['compilationDescr'], sol['compilationExecution'],
               solDir, getCacheDir(sol['compilationDescr']['files'], 'c-solution'), baseWorkingDir, 'solution')
        report['solutions'].append({'id': sol['id'], 'compilationExecution': solReport})
        solutionsInfo[sol['id']] = (sol['compilationDescr']['language'], sol['compilationDescr']['files'])
        if isExecError(solReport):
            # We keep a list of solutions with errors
            solutionsWithErrors.append(sol['id'])

    # *** Executions
    os.mkdir(baseWorkingDir + "executions/")
    report['executions'] = []
    for test in evaluationParams['executions']:
        if test['idSolution'] in solutionsWithErrors:
            # This solution didn't compile
            continue

        (solutionLang, solutionFiles) = solutionsInfo[test['idSolution']]

        mainTestReport = {'name': test['idSolution'], 'testsReports': []}
        testDir = "%sexecutions/%s.%s/" % (baseWorkingDir, test['idSolution'], test['id'])
        os.mkdir(testDir)

        # Files to test as input
        testFiles = []
        for filterGlob in test['filterTests']:
            testFiles.extend(glob.glob(baseWorkingDir + 'tests/' + filterGlob))

        for tf in testFiles:
            # We execute everything for each test file tf
            if '.' in os.path.basename(tf):
                baseTfName = '.'.join(os.path.basename(tf).split('.')[:-1])
            else:
                baseTfName = os.path.basename(tf)
            
            subTestReport = {'name': baseTfName}
            # We execute the sanitizer
            filecopy(baseWorkingDir + 'sanitizer/sanitizer.exe', testDir + 'sanitizer.exe')
            subTestReport['sanitizer'] = cachedExecute(evaluationParams['checker']['runExecution'],
                    'sanitizer.exe', testDir,
                    getCacheDir(evaluationParams['sanitizer']['compilationDescr']['files'], 'e-sanitizer', inputFiles=[tf]),
                    stdinFile=tf, outputFiles=[])
            if isExecError(subTestReport['sanitizer']):
                # Sanitizer found an error, we skip this file
                mainTestReport['testsReports'].append(subTestReport)
                continue
            # We execute the solution
            filecopy(tf, testDir, fromlocal=True)
            filecopy("%ssolutions/%s/solution.exe" % (baseWorkingDir, test['idSolution']), testDir + 'solution.exe', fromlocal=True)
            subTestReport['execution'] = cachedExecute(test['runExecution'], 'solution.exe', testDir,
                    getCacheDir(solutionFiles, 'e-solution', inputFiles=[testDir + baseTfName + '.in']),
                    stdinFile=testDir + baseTfName + '.in', stdoutFile=testDir + baseTfName + '.solout',
                    outputFiles=[baseTfName + '.solout'], language=solutionLang)
            if isExecError(subTestReport['execution']):
                # Solution returned an error, no need to check
                mainTestReport['testsReports'].append(subTestReport)
                continue
            # We execute the checker
            filecopy(baseWorkingDir + 'checker/checker.exe', testDir)
            if os.path.isfile(tf[:-3] + '.out'):
                filecopy(tf[:-3] + '.out', testDir, fromlocal=True)
            else:
                # We write a dummy .out file, the checker probably doesn't need it
                open(testDir + baseTfName + '.out', 'w')
            subTestReport['checker'] = cachedExecute(evaluationParams['checker']['runExecution'],
                    "checker.exe %s %s %s" % (baseTfName + '.solout', baseTfName + '.in', baseTfName + '.out'),
                    testDir,
                    getCacheDir(evaluationParams['checker']['compilationDescr']['files'], 'e-checker',
                    inputFiles=[testDir + baseTfName + '.solout', testDir + baseTfName + '.in', testDir + baseTfName + '.out']),
                    stdinFile=testDir + baseTfName + '.out',
                    stdoutFile=testDir + baseTfName + '.ok',
                    outputFiles=[testDir + baseTfName + '.ok'])
            mainTestReport['testsReports'].append(subTestReport)

        report['executions'].append(mainTestReport)

    # We validate the output JSON format
    try:
        validate(report, json.load(open(CFG_OUTPUTSCHEMA, 'r')))
    except Exception as err:
        raise Exception("Validation failed for output JSON, error message: %s" % str(err))

    return report


if __name__ == '__main__':
    try:
        inJson = json.load(sys.stdin)
    except Exception as err:
        raise Exception("Input data is not valid JSON: %s" % err)
    json.dump(evaluation(inJson), sys.stdout)
