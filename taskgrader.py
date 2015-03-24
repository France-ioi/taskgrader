#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT


import glob, hashlib, json, os, random, shlex, shutil, sqlite3, sys, subprocess
from config import *

sys.path.append(CFG_JSONSCHEMA)
from jsonschema import validate

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
        if (type(val) is str or type(val) is unicode) and len(val) > 0:
            if val[0] == '@':
                # It's a variable, we replace it with the JSON data
                # It will return an error if the variable doesn't exist, it's intended
                return self.__getvalue__(self.varData[val[1:]])
            elif '$' in val:
                if '$BUILD_PATH' in val:
                    return self.__getvalue__(val.replace('$BUILD_PATH', self.varData['BUILD_PATH']))
                elif '$ROOT_PATH' in val:
                    return self.__getvalue__(val.replace('$ROOT_PATH', self.varData['ROOT_PATH']))
                elif '$TASK_PATH' in val:
                    return self.__getvalue__(val.replace('$TASK_PATH', self.varData['TASK_PATH']))
            else:
                return val
        elif type(val) is dict:
            # It's a dict, we replace it with a dictWithVars
            return dictWithVars(self.varData, initDict=val)
        elif type(val) is list:
            # It's a list, we filter the values in it
            newval = map(self.__getvalue__, val)
            # We remove None values, which are probably undefined variables
            while None in newval:
                newval.remove(None)
            return newval
        else:
            return val

    def __getitem__(self, key):
        # We only need to change how values are returned
        return self.__getvalue__(super(dictWithVars, self).__getitem__(key))


def isExecError(executionReport):
    """Returns whether an execution returned an error according to its exit code."""
    return (executionReport['exitCode'] != 0)


def getFile(fileDescr, workingDir, buildDir=None, language=''):
    """Fetch a file contents from a fileDescr object into workingDir.
    If getCache is True, also lookup cache for related cached files."""

    if os.path.isfile(workingDir + fileDescr['name']):
        # File already exists
        raise Exception("File %s already exists in %s" % (fileDescr['name'], workingDir))

    if '/' in fileDescr['name']:
        # Need to make a folder
        try:
            os.makedirs(workingDir + fileDescr['name'].split('/')[0])
        except:
            pass
        

    if fileDescr.has_key('content'): # Content given in descr
        open(workingDir + fileDescr['name'], 'w').write(fileDescr['content'])
    elif fileDescr.has_key('path'): # Get file by path
        if os.path.isfile(fileDescr['path']):
            os.symlink(fileDescr['path'], workingDir + fileDescr['name'])
        else:
            raise Exception("File not found: %s" % fileDescr['path'])
    else: # File is a built dependency
        if not buildDir:
            buildDir = workingDir
        if os.path.isfile('%slibs/%s-%s' % (buildDir, language, fileDescr['name'])):
            # We search for [language]-[name] in the libs directory
            os.symlink('%slibs/%s-%s' % (buildDir, language, fileDescr['name']), workingDir + fileDescr['name'])
        elif language == 'cpp' and os.path.isfile('%slibs/c-%s' % (buildDir, fileDescr['name'])):
            # For cpp, we also search for c-[name] in the libs directory
            os.symlink('%slibs/c-%s' % (buildDir, fileDescr['name']), workingDir + fileDescr['name'])
        elif language in ['py', 'py2', 'py3'] and os.path.isfile('%slibs/run-%s' % (buildDir, fileDescr['name'])):
            # For Python languages, we search for run-[name] in the libs directory
            os.symlink('%slibs/run-%s' % (buildDir, fileDescr['name']), workingDir + fileDescr['name'])
        elif os.path.isfile('%slibs/%s' % (buildDir, fileDescr['name'])):
            # We search for [name] in the libs directory
            os.symlink('%slibs/%s' % (buildDir, fileDescr['name']), workingDir + fileDescr['name'])
        else:
            raise Exception("Dependency not found: %s for language %s" % (fileDescr['name'], language))
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
            fileHashList.append(hashlib.md5(open(fileDescr['path'], 'rb').read()).hexdigest())

    # We add identifiers for input files (local name and md5sum)
    for f in inputFiles:
        fileIdList.append("input:%s" % os.path.basename(f))
        fileHashList.append(hashlib.md5(open(f, 'rb').read()).hexdigest())

    fileIdList.sort()
    fileHashList.sort() # Both lists won't be sorted the same but it's not an issue

    # We make a text version for the database
    fileHashes = ';'.join(fileHashList)
    # This will be the ID string in the database, containing the cache type and the source files list
    filesId = "cache:%s;%s" % (cacheType, ";".join(fileIdList))

    # Read cache information from database
    dbCur = CFG_DATABASE.cursor()
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
            CFG_DATABASE.commit()
            try:
                shutil.rmtree("%s%s" % (CFG_CACHEDIR, dbId))
            except:
                pass
            os.mkdir("%s%s/" % (CFG_CACHEDIR, dbId))
            return (False, "%s%s/" % (CFG_CACHEDIR, dbId))
    else:
        # New entry in database
        dbCur.execute("INSERT INTO cache(filesid, hashlist) VALUES(?, ?)", [filesId, fileHashes])
        CFG_DATABASE.commit()
        newId = dbCur.lastrowid
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


def execute(executionParams, cmdLine, workingDir, stdinFile=None, stdoutFile=None, language='', isolate=True):
    """Execute a command line and build the report."""
    # Check time and memory limits
    if executionParams['timeLimitMs'] > 60000:
        raise Exception("Time limit (%d) for command %s too high." % (executionParams['timeLimitMs'], cmdLine))
    if executionParams['memoryLimitKb'] > 1024*1024:
        raise Exception("Memory limit (%d) for command %s too high." % (executionParams['memoryLimitKb'], cmdLine))

    # Values copied from the arguments
    report = {'timeLimitMs': executionParams['timeLimitMs'],
            'memoryLimitKb': executionParams['memoryLimitKb'],
            'commandLine': cmdLine,
            'wasCached': False}

    # Transformation of time and memory limits for the language
    if CFG_TRANSFORM_MEM.has_key(language):
        realMemLimit = CFG_TRANSFORM_MEM[language](executionParams['memoryLimitKb'])
    else:
        realMemoryLimitKb = executionParams['memoryLimitKb']
    if CFG_TRANSFORM_TIME.has_key(language):
        (timeTransform, timeUntransform) = CFG_TRANSFORM_TIME[language]
        realTimeLimit = timeTransform(executionParams['timeLimitMs'])
        report['realTimeLimitMs'] = realTimeLimit
    else:
        timeUntransform = None
        realTimeLimit = executionParams['timeLimitMs']

    if stdoutFile == None:
        stdoutFile = workingDir + 'stdout'

    if isolate:
        # Initialize isolate box
        initProc = subprocess.Popen([CFG_ISOLATEBIN, '--init'], stdout=subprocess.PIPE, cwd=workingDir)
        (isolateDir, isolateErr) = initProc.communicate()
        initProc.wait()
        # isolatePath will be the path of the sandbox, as given by isolate
        isolateDir = isolateDir.strip() + '/box/'

        # Build isolate command line
        isolatedCmdLine  = CFG_ISOLATEBIN
        isolatedCmdLine += ' --processes'
        isolatedCmdLine += ' --env=HOME --env=PATH'
        isolatedCmdLine += ' --meta=' + workingDir + 'isolate.meta'
        if executionParams['timeLimitMs'] > 0:
            isolatedCmdLine += ' --time=' + str(realTimeLimit / 1000.)
        if executionParams['memoryLimitKb'] > 0:
            isolatedCmdLine += ' --mem=' + str(executionParams['memoryLimitKb'])
        if stdinFile:
            if os.path.isfile(stdinFile):
                shutil.copy(stdinFile, isolateDir + 'isolated.stdin')
                isolatedCmdLine += ' --stdin=isolated.stdin'
            else:
                raise Exception("Input file %s not found while preparing to execute command %s." % (stdinFile, cmdLine))
        isolatedCmdLine += ' --stdout=isolated.stdout --stderr=isolated.stderr'
        isolatedCmdLine += ' --run -- ' + cmdLine

        # Copy files from working directory to sandbox
        for f in os.listdir(workingDir):
            shutil.copy(workingDir + f, isolateDir + f)

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
                shutil.copy(isolateDir + f, workingDir + f)
        shutil.copy(isolateDir + 'isolated.stdout', stdoutFile)

        # Get metadata from isolate execution
        isolateMeta = {}
        for l in open(workingDir + 'isolate.meta', 'r').readlines():
            [name, val] = l.split(':', 1)
            isolateMeta[name] = val.strip()

        # Generate execution report
        if isolateMeta.has_key('time'):
            if timeUntransform:
                report['timeTakenMs'] = timeUntransform(float(isolateMeta['time'])*1000)
                report['realTimeTakenMs'] = float(isolateMeta['time'])*1000
            else:
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
            if os.path.isfile(stdinFile):
                stdinHandle = open(stdinFile, 'r')  
            else:
                raise Exception("Input file %s not found while preparing to execute command %s." % (stdinFile, cmdLine))
        else:
            stdinHandle = None
        proc = subprocess.Popen(shlex.split(cmdLine), stdin=stdinHandle, stdout=open(stdoutFile, 'w'),
                stderr=open(workingDir + 'stderr', 'w'), cwd=workingDir)

        proc.wait()

        # Generate execution report
        report['timeTakenMs'] = -1 # We don't know
        report['wasKilled'] = False
        report['exitCode'] = proc.returncode

        report['stdout'] = capture(stdoutFile, name='stdout',
                truncateSize=executionParams['stdoutTruncateKb'] * 1024)
        report['stderr'] = capture(workingDir + 'stderr', name='stderr',
                truncateSize=executionParams['stderrTruncateKb'] * 1024)

    filesReports = []
    for globf in executionParams['getFiles']:
        for f in glob.glob(workingDir + globf):
            # Files captured are always truncated at 1MB
            filesReports.append(capture(f, name=os.path.basename(f), truncateSize=1024*1024))
    report['files'] = filesReports

    return report


def cachedExecute(executionParams, cmdLine, workingDir, cacheData, stdinFile=None, stdoutFile=None, outputFiles=[], language=''):
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
            report = execute(executionParams, cmdLine, workingDir, stdinFile=stdinFile, stdoutFile=stdoutFile, language=language)
            # We save results to cache if execution was successful
            if not isExecError(report):
                for g in outputFiles:
                    for f in glob.glob(workingDir + g):
                        shutil.copy(f, cacheDir)
                json.dump(report, open("%srunExecution.json" % cacheDir, 'w'))
                open("%scache.ok" % cacheDir, 'w')
    else:
        # We don't use cache at all
        report = execute(executionParams, cmdLine, workingDir, stdinFile=stdinFile, stdoutFile=stdoutFile, language=language)

    return report


def compile(compilationDescr, executionParams, workingDir, buildDir='./', name='executable'):
    """Effectively compile a program, not using cache (probably because
    there's no cached version)."""
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
    elif compilationDescr['language'] in ['sh', 'py', 'py3']:
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
        if compilationDescr['language'] == 'sh':
            sharFile.write("export TASKGRADER_DEPFILES=\"%s\"\n" % ' '.join(depFiles))
            sharFile.writelines(map(lambda x: "/bin/sh %s $@\n" % x, sourceFiles))
        elif compilationDescr['language'] == 'py':
            sharFile.write("/usr/bin/python2 %s $@" % ' '.join(sourceFiles))
        elif compilationDescr['language'] == 'py3':
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
                'wasKilled': False,
                'wasCached': False,
                'exitCode': 0}
    return report


def cachedCompile(compilationDescr, executionParams, workingDir, cacheData, buildDir='./', name='executable'):
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
            report = compile(compilationDescr, executionParams, workingDir, buildDir=buildDir, name=name)
            # We cache the results if compilation was successful
            if not isExecError(report):
                shutil.copy("%s%s.exe" % (workingDir, name), cacheDir)
                json.dump(report, open("%scompilationExecution.json" % cacheDir, 'w'))
                open("%scache.ok" % cacheDir, 'w')
    else:
        # We don't use cache at all
        report = compile(compilationDescr, compilationExecution, workingDir, buildDir=buildDir, name=name)

    return report


def evaluation(evaluationParams):
    """Full evaluation process."""

    # *** Variables handling
    varData = {'ROOT_PATH': evaluationParams['rootPath'],
               'TASK_PATH': evaluationParams['taskPath']}

    # We load a "preprocessing" JSON node or file
    try:
        varData.update(json.load(open(os.path.join(evaluationParams['taskPath'], 'defaultParams.json'), 'r')))
    except:
        pass
    if evaluationParams.has_key('extraParams'):
        if type(evaluationParams['extraParams']) is str:
            varData.update(json.load(open(evaluationParams['extraParams'], 'r')))
        else:
            varData.update(evaluationParams['extraParams'])
    evaluationParams = dictWithVars(varData, initDict=evaluationParams)

    # Path where the evaluation will take place
    if evaluationParams.has_key('outputPath'):
        baseWorkingDir = CFG_BUILDSDIR + evaluationParams['outputPath']
    else:
        baseWorkingDir = CFG_BUILDSDIR + '_build' + str(random.randint(0, 10000)) + '/'
        while os.path.isdir(baseWorkingDir):
            baseWorkingDir = CFG_BUILDSDIR + '_build' + str(random.randint(0, 10000)) + '/'
    os.mkdir(baseWorkingDir)

    report = {}

    varData['BUILD_PATH'] = baseWorkingDir
    report['buildPath'] = baseWorkingDir

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
                    shutil.copy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idGenerator'], genDir + 'generator.exe')
                    genReport['generatorExecution'] = cachedExecute(gen['genExecution'], "generator.exe %s" % tc['params'], genDir,
                            getCacheDir(generatorsFiles[gen['idGenerator']], 'e-generator:' + tc['params']),
                            stdoutFile=genDir + tc['name'] + '.in',
                            outputFiles=[tc['name'] + '.in'])
                    if not isExecError(genReport['generatorExecution']):
                        shutil.copy(genDir + tc['name'] + '.in', baseWorkingDir + 'tests/' + tc['name'] + '.in')

                    shutil.copy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idOutputGenerator'], genDir + 'outgenerator.exe')
                    genReport['outputGeneratorExecution'] = cachedExecute(gen['outGenExecution'], "outgenerator.exe %s" % tc['params'], genDir,
                            getCacheDir(generatorsFiles[gen['idOutputGenerator']], 'e-generator:' + tc['params']),
                            stdoutFile=genDir + tc['name'] + '.out',
                            outputFiles=[tc['name'] + '.out'])
                    if not isExecError(genReport['outputGeneratorExecution']):
                        shutil.copy(genDir + tc['name'] + '.out', baseWorkingDir + 'tests/' + tc['name'] + '.out')
                    errorSoFar = errorSoFar or isExecError(genReport['generatorExecution']) or isExecError(genReport['outputGeneratorExecution'])
                else:
                    # We only have one generator, we assume `name` is the name of the test file to generate
                    shutil.copy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idGenerator'], genDir + 'generator.exe')
                    genReport['generatorExecution'] = cachedExecute(gen['genExecution'], "generator.exe %s" % tc['params'], genDir,
                            getCacheDir(generatorsFiles[gen['idGenerator']], 'e-generator:' + tc['params']),
                            stdoutFile=genDir + tc['name'],
                            outputFiles=[tc['name']])
                    if isExecError(genReport['generatorExecution']):
                        errorSoFar = True
                    else:
                        shutil.copy(genDir + tc['name'], baseWorkingDir + 'tests/' + tc['name'])
                report['generations'].append(genReport)
                
        else:
            # We generate the test cases just by executing the generators
            genReport = {'id': gen['id']}
            shutil.copy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idGenerator'], genDir + 'generator.exe')
            genReport['generatorExecution'] = cachedExecute(gen['genExecution'], "generator.exe", genDir,
                    getCacheDir(generatorsFiles[gen['idGenerator']], 'e-generator'), outputFiles=['*.in', '*.out', '*.h', '*.java', '*.ml', '*.mli', '*.pas', '*.py'])
            errorSoFar = errorSoFar or isExecError(genReport['generatorExecution'])
            if gen.has_key('idOutputGenerator'):
                # We also have an output generator
                shutil.copy(baseWorkingDir + 'generators/%s/generator.exe' % gen['idOutputGenerator'], genDir + 'outgenerator.exe')
                genReport['outputGeneratorExecution'] = cachedExecute(gen['outGenExecution'], "outgenerator.exe" % gen['idOutputGenerator'], genDir,
                        getCacheDir(generatorsFiles[gen['idOutputGenerator']], 'e-generator'), outputFiles=['*.out'])
                errorSoFar = errorSoFar or isExecError(genReport['outputGeneratorExecution'])
            report['generations'].append(genReport)
            # We copy the generated test files
            for f in (glob.glob(genDir + '*.in') + glob.glob(genDir + '*.out')):
                shutil.copy(f, baseWorkingDir + 'tests/')
            # We copy the generated lib files
            libFiles = []
            for ext in ['*.h', '*.java', '*.ml', '*.mli', '*.pas', '*.py']:
                libFiles.extend(glob.glob(genDir + ext))
            for f in libFiles:
                shutil.copy(f, baseWorkingDir + 'libs/')

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
            shutil.copy(baseWorkingDir + 'sanitizer/sanitizer.exe', testDir + 'sanitizer.exe')
            subTestReport['sanitizer'] = cachedExecute(evaluationParams['checker']['runExecution'],
                    'sanitizer.exe', testDir,
                    getCacheDir(evaluationParams['sanitizer']['compilationDescr']['files'], 'e-sanitizer', inputFiles=[tf]),
                    stdinFile=tf, outputFiles=[])
            if isExecError(subTestReport['sanitizer']):
                # Sanitizer found an error, we skip this file
                mainTestReport['testsReports'].append(subTestReport)
                continue
            # We execute the solution
            shutil.copy(tf, testDir)
            shutil.copy("%ssolutions/%s/solution.exe" % (baseWorkingDir, test['idSolution']), testDir + 'solution.exe')
            subTestReport['execution'] = cachedExecute(test['runExecution'], 'solution.exe', testDir,
                    getCacheDir(solutionFiles, 'e-solution', inputFiles=[testDir + baseTfName + '.in']),
                    stdinFile=testDir + baseTfName + '.in', stdoutFile=testDir + baseTfName + '.solout',
                    outputFiles=['*.solout'], language=solutionLang)
            if isExecError(subTestReport['execution']):
                # Solution returned an error, no need to check
                mainTestReport['testsReports'].append(subTestReport)
                continue
            # We execute the checker
            shutil.copy(baseWorkingDir + 'checker/checker.exe', testDir)
            if os.path.isfile(tf[:-3] + '.out'):
                shutil.copy(tf[:-3] + '.out', testDir)
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