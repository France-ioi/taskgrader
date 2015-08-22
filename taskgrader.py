#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This simple tool manages every step of grading a contest task, from the
# generation of test data to the grading of a solution output.
# See README.md for more information.


import cPickle, fcntl, glob, hashlib, json, os, random, shlex, shutil, sqlite3
import stat, sys, subprocess, time, traceback
from config import *

sys.path.append(CFG_JSONSCHEMA)
from jsonschema import validate


class TemporaryException(Exception):
    """TemporaryException is a special exception representing a temporary
    error, for which reexecuting the exact same evaluation can succeed at a
    later time."""

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class CacheFolder(object):
    """CacheFolder represents a folder of the cache, caching a specific
    execution. The class gives functions for reading from and writing to this
    folder."""

    def __init__(self, cacheId):
        """cacheId is the ID number of the cache folder."""
        self.cacheId = cacheId
        self.cacheFolder = os.path.join(CFG_CACHEDIR, "%s/" % cacheId)

        try:
            os.mkdir(self._makePath())
        except:
            pass

        # Lock the cache folder
        locking_start = time.time()
        self.cacheLock = open(self._makePath('cache.lock'), 'w+')
        while time.time() - locking_start < CFG_CACHE_TIMEOUT:
            # There's no internal timeout function, we have to do it manually
            try:
                fcntl.lockf(self.cacheLock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except IOError:
                continue
        if time.time() - locking_start > CFG_CACHE_TIMEOUT:
            raise TemporaryException("Failed to acquire lock on cache folder #%d after %d seconds." % (self.cacheId, CFG_CACHE_TIMEOUT))

        self.isCached = os.path.isfile(self._makePath('cache.ok'))
        self.files = []
        if self.isCached:
            try:
                self.files = cPickle.load(open(self._makePath('cache.files'), 'r'))
            except:
                pass

    def __del__(self):
        # Unlock the cache folder
        fcntl.lockf(self.cacheLock, fcntl.LOCK_UN)

    def _makePath(self, f=None):
        """Makes the path to the file f in the cache folder."""
        if f:
            return os.path.join(CFG_CACHEDIR, str(self.cacheId), f)
        else:
            return os.path.join(CFG_CACHEDIR, "%s/" % self.cacheId)

    def invalidate(self):
        """Invalidates the cache folder, removing all files."""
        try:
            shutil.rmtree(self._makePath())
        except:
            pass
        os.mkdir(self._makePath())
        self.isCached = False
        self.files = []

    def addFile(self, path, isExecutable=False):
        """Add a file to the cache. save() must be called in order for the
        cache to be considered as complete."""
        # If the cache has already been made, we don't allow modification.
        if self.isCached:
            raise Exception("Tried to modify an already cached version (ID %d)." % self.cacheId)

        filename = os.path.basename(path)
        filecopy(path, self._makePath(filename))
        if isExecutable:
            os.chmod(self._makePath(filename), 493)
        self.files.append(filename)

    def addReport(self, data):
        """Add the execution report to the cache. save() must be called in
        order for the cache to be considered as complete."""
        # If the cache has already been made, we don't allow modification.
        if self.isCached:
            raise Exception("Tried to modify an already cached version (ID %d)." % self.cacheId)

        json.dump(data, open(self._makePath('report.json'), 'w'))

    def save(self):
        """Save the cache, marking it as complete and usable."""
        cPickle.dump(self.files, open(self._makePath('cache.files'), 'w'))
        open(self._makePath('cache.ok'), 'w').write(' ')
        self.isCached = True

    def loadFiles(self, path):
        """Load files from the cache into the folder path. Will behave as if
        the execution took place in that folder."""
        if not self.isCached:
            raise Execption("Tried to load non-cached files from cache (ID %d)." % self.cacheId)

        for f in self.files:
            symlink(self._makePath(f), os.path.join(path, f))

    def loadReport(self):
        """Load the execution report from the cache."""
        if not self.isCached:
            raise Execption("Tried to load non-cached files from cache (ID %d)." % self.cacheId)

        return json.load(open(self._makePath('report.json'), 'r'))


class CacheHandle():
    """CacheHandle represents a program in the cache. It allows to get
    CacheFolder instances related to that program."""

    def __init__(self, database, programFiles):
        """database is the cache database.
        programFiles is the list of fileDescr elements representing the
        program."""
        self.database = database

        fileIdList = []
        fileHashList = []
        # We build a list of identifiers for each source file and compute their md5
        for fileDescr in programFiles:
            if fileDescr.has_key('content'):
                # File content is given, we use the name given and the hash as reference
                md5sum = hashlib.md5(fileDescr['content'].encode('utf-8', errors='ignore')).hexdigest()
                fileIdList.append("file:%s:%s" % (fileDescr['name'], md5sum))
            elif fileDescr.has_key('path'):
                # File path is given, we use the path as reference
                filePath = os.path.abspath(os.path.realpath(fileDescr['path']))
                md5sum = hashlib.md5(open(filePath, 'rb').read()).hexdigest()
                fileIdList.append("path:%s" % filePath)
                fileHashList.append(md5sum)
            else:
                # It's a local dependency
                fileIdList.append("local:%s" % fileDescr['name'])

        fileIdList.sort()
        fileHashList.sort() # Both lists won't be sorted the same but it's not an issue

        self.programId = "program:%s" % (';'.join(fileIdList))
        self.programHashes = ';'.join(fileHashList)


    def getCacheFolder(self, cacheType, args='', inputFiles=[]):
        """Returns the CacheFolder for the program executed with args and
        inputFiles as input.
        cacheType represents the type of cache (compilation, execution); it
        must be the same string among all executions of the program."""

        inputIdList = []
        # We add identifiers for input files (local name and md5sum)
        for f in inputFiles:
            md5sum = hashlib.md5(open(f, 'rb').read()).hexdigest()
            inputIdList.append("input:%s:%s" % (os.path.basename(f), md5sum))

        # This will be the ID string in the database, containing the cache type and the input files list
        filesId = "%s;cache:%s;args:%s;%s" % (self.programId, cacheType, args, ";".join(inputIdList))

        # Read cache information from database
        dbCur = self.database.cursor()
        dbCur.execute("SELECT * FROM cache WHERE filesId=?", [filesId])
        dbRow = dbCur.fetchone()
        if dbRow:
            # This list of files already exists in the database
            dbId = dbRow['id']
            dbHashes = dbRow['hashlist']
            if dbHashes == self.programHashes:
                # MD5 hashes are good
                return CacheFolder(dbId)
            else:
                # MD5 hashes changed, update database, invalidate cache
                dbCur.execute("UPDATE cache SET hashlist=? WHERE filesid=?", [self.programHashes, filesId])
                self.database.commit()
                cf = CacheFolder(dbId)
                cf.invalidate()
                return cf
        else:
            # New entry in database
            dbCur.execute("INSERT INTO cache(filesid, hashlist) VALUES(?, ?)", [filesId, self.programHashes])
            self.database.commit()
            newId = dbCur.lastrowid
            return CacheFolder(newId)


class CacheDatabase():
    """Represents the cache database."""

    def __init__(self):
        self.database = sqlite3.connect(CFG_CACHEDBPATH)
        self.database.row_factory = sqlite3.Row

    def getHandle(self, files):
        return CacheHandle(self.database, files)


class Execution():
    """Represents an execution of a program.
    It is first created with the program parameters: executable, parameters of
    execution, command-line; the function execute then allows multiple
    executions of the program in different folders and with different
    arguments."""

    def __init__(self, executablePath, executionParams, cmd, language=''):
        # Check time and memory limits
        if executionParams['timeLimitMs'] > CFG_MAX_TIMELIMIT:
            raise Exception("Time limit (%d) for command %s too high." % (executionParams['timeLimitMs'], cmdLine))
        if executionParams['memoryLimitKb'] > CFG_MAX_MEMORYLIMIT:
            raise Exception("Memory limit (%d) for command %s too high." % (executionParams['memoryLimitKb'], cmdLine))

        self.executablePath = executablePath
        self.executionParams = executionParams
        self.cmd = cmd
        self.language = language

        # Transformation of time and memory limits for the language
        self.realMemoryLimitKb = CFG_TRANSFORM_MEM.get(language, CFG_TRANSFORM_MEM_DEFAULT)(executionParams['memoryLimitKb'])

        (timeTransform, self.timeUntransform) = CFG_TRANSFORM_TIME.get(language, CFG_TRANSFORM_TIME_DEFAULT)
        self.realTimeLimit = timeTransform(executionParams['timeLimitMs'])

        # Report values from arguments
        self.baseReport = {'timeLimitMs': self.executionParams['timeLimitMs'],
            'memoryLimitKb': self.executionParams['memoryLimitKb'],
            'wasCached': False,
            'realMemoryLimitKb': self.realMemoryLimitKb,
            'realTimeLimitMs': self.realTimeLimit}


    def _prepareExecute(self, workingDir, stdinFile=None, stdoutFile=None):
        """Prepares the execution in workingDir, checks stdinFile and
        stdoutFile paths."""

        # Copy executable to workingDir
        if self.executablePath:
            try:
                symlink(self.executablePath, os.path.join(workingDir, os.path.basename(self.executablePath)))
            except:
                # The executable was probably already imported
                pass

        # Check input file path
        if not stdinFile:
            pass
        elif not os.path.isfile(stdinFile):
            raise Exception("Input file `%s` not found while preparing to execute command `%s`." % (stdinFile, cmdLine))
        elif not isInRestrict(stdinFile):
            raise Exception("Using `%s` as input file not allowed." % stdinFile)
        self.stdinFile = stdinFile

        # Make stdoutFile path
        if stdoutFile == None:
            self.stdoutFile = workingDir + 'stdout'
        elif not isInRestrict(stdoutFile):
            raise Exception("Writing to file `%s` not allowed." % stdoutFile)
        else:
            self.stdoutFile = stdoutFile


    def _doExecute(self, workingDir, args=None):
        """Executes the command in workingDir with args."""

        cmdLine = self.cmd + ((' ' + args) if args else '')

        # Open stdin file
        stdinHandle = (open(self.stdinFile, 'rb') if self.stdinFile else None)

        proc = subprocess.Popen(shlex.split(cmdLine), stdin=stdinHandle, stdout=open(self.stdoutFile, 'w'),
                stderr=open(workingDir + 'stderr', 'w'), cwd=workingDir)
        proc.wait()

        # Make execution report
        report = {}
        report.update(self.baseReport)
        report.update({
                'commandLine': cmdLine,
                'timeTakenMs': -1, # We don't know
                'realTimeTakenMs': -1, # We don't know
                'wasKilled': False,
                'exitCode': proc.returncode,
                'exitSig': -1 # We don't know
            })

        report['stdout'] = capture(self.stdoutFile, name='stdout',
                truncateSize=self.executionParams['stdoutTruncateKb'] * 1024)
        report['stderr'] = capture(workingDir + 'stderr', name='stderr',
                truncateSize=self.executionParams['stderrTruncateKb'] * 1024)

        filesReports = []
        for globf in self.executionParams['getFiles']:
            for f in glob.glob(workingDir + globf):
                filesReports.append(capture(f, name=os.path.basename(f), truncateSize=CFG_MAX_GETFILE))
        report['files'] = filesReports

        return report


    def execute(self, workingDir, args=None, stdinFile=None, stdoutFile=None):
        """Execute the program in workingDir, with command-line arguments args,
        and standard input and output redirected from stdinFile and to
        stdoutFile."""
        self.workingDir = workingDir
        self._prepareExecute(workingDir, stdinFile, stdoutFile)
        return self._doExecute(workingDir, args)


class IsolatedExecution(Execution):
    """Represents an execution encapsulated in isolate."""

    def _doExecute(self, workingDir, args=None):
        cmdLine = self.cmd + ((' ' + args) if args else '')
        report = {}
        report.update(self.baseReport)

        # Box ID is required if multiple isolate instances are running concurrently
        boxId = (os.getpid() % 100)

        isolateCommonOpts = ['--box-id=%d' % boxId]
        if CFG_CONTROLGROUPS:
            isolateCommonOpts.append('--cg')

        # Initialize isolate box
        initProc = subprocess.Popen([CFG_ISOLATEBIN, '--init'] + isolateCommonOpts, stdout=subprocess.PIPE, cwd=workingDir)
        (isolateDir, isolateErr) = initProc.communicate()
        initProc.wait()

        if initProc.returncode > 0:
            raise Exception("Error while initializing isolate box (#%d)." % initProc.returncode)

        # isolatePath will be the path of the sandbox, as given by isolate
        isolateDir = isolateDir.strip() + '/box/'

        # Build isolate command line
        isolatedCmdLine  = CFG_ISOLATEBIN
        isolatedCmdLine += ' --processes'
        isolatedCmdLine += ' --env=HOME --env=PATH'
        isolatedCmdLine += ' --meta=' + workingDir + 'isolate.meta'
        # Use an unique box ID
        isolatedCmdLine += ' --box-id=%d' % boxId
        if self.executionParams['timeLimitMs'] > 0:
            isolatedCmdLine += ' --time=' + str(self.realTimeLimit / 1000.)
        if self.executionParams['memoryLimitKb'] > 0:
            if CFG_CONTROLGROUPS:
                isolatedCmdLine += ' --cg-mem=' + str(self.realMemoryLimitKb)
            else:
                isolatedCmdLine += ' --mem=' + str(self.realMemoryLimitKb)
        if self.stdinFile:
            filecopy(self.stdinFile, isolateDir + 'isolated.stdin', fromlocal=True)
            isolatedCmdLine += ' --stdin=isolated.stdin'
        if CFG_CONTROLGROUPS:
            isolatedCmdLine += ' --cg --cg-timing'
        isolatedCmdLine += ' --stdout=isolated.stdout --stderr=isolated.stderr'
        isolatedCmdLine += ' --run -- ' + cmdLine

        # Clean old stdout/stderr files
        try:
            os.unlink(os.path.join(workingDir, 'isolated.stdout'))
        except:
            pass
        try:
            os.unlink(os.path.join(workingDir, 'isolated.stderr'))
        except:
            pass
        # Copy files from working directory to sandbox
        for f in os.listdir(workingDir):
            filecopy(workingDir + f, isolateDir + f)

        # Create meta file with right owner/permissions
        open(workingDir + 'isolate.meta', 'w')

        # Execute the isolated program
        proc = subprocess.Popen(shlex.split(isolatedCmdLine), cwd=workingDir)
        proc.wait()

        # Get metadata from isolate execution
        isolateMeta = {}
        try:
            for l in open(workingDir + 'isolate.meta', 'r').readlines():
                [name, val] = l.split(':', 1)
                isolateMeta[name] = val.strip()
        except:
            pass

        if proc.returncode > 1:
            # Isolate error (0 and 1 refer to the program inside the sandbox)
            # Try to cleanup sandbox
            cleanProc = subprocess.Popen([CFG_ISOLATEBIN, '--cleanup', '--box-id=%d' % boxId], cwd=workingDir)
            cleanProc.wait()
            raise Exception("""Internal isolate error, please check installation: #%d %s
                    while trying to execute `%s` in folder `%s`""" % (proc.returncode,
                    isolateMeta.get('status', ''), cmdLine, workingDir))

        # Set file rights so that we can access the files
        rightsProc = subprocess.Popen([CFG_RIGHTSBIN])
        rightsProc.wait()

        # Copy back the files from sandbox
        for f in os.listdir(isolateDir):
            if os.path.isfile(isolateDir + f) and not os.path.isfile(workingDir + f):
                filecopy(isolateDir + f, workingDir + f)
        filecopy(isolateDir + 'isolated.stdout', self.stdoutFile)

        # Generate execution report
        if isolateMeta.has_key('time'):
            report['realTimeTakenMs'] = int(float(isolateMeta['time'])*1000)
            report['timeTakenMs'] = int(self.timeUntransform(report['realTimeTakenMs']))
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
        report['commandLine'] = cmdLine
        report['wasKilled'] = isolateMeta.has_key('killed')
        report['exitCode'] = int(isolateMeta.get('exitcode', proc.returncode))
        if isolateMeta.get('status', '') == 'TO':
            # Timed-out, custom value
            report['exitSig'] = 137
        elif isolateMeta.get('status', '') == 'SG':
            report['exitSig'] = int(isolateMeta.get('exitsig', 0))
        else:
            report['exitSig'] = 0

        report['stdout'] = capture(workingDir + 'isolated.stdout', name='stdout',
                truncateSize=self.executionParams['stdoutTruncateKb'] * 1024)
        report['stderr'] = capture(workingDir + 'isolated.stderr', name='stderr',
                truncateSize=self.executionParams['stderrTruncateKb'] * 1024)

        # Cleanup sandbox
        cleanProc = subprocess.Popen([CFG_ISOLATEBIN, '--cleanup'] + isolateCommonOpts, cwd=workingDir)
        cleanProc.wait()

        return report


class Language():
    """Represents a language, gives functions for aspects specific to each
    language."""

    lang = 'default'

    def _getPossiblePaths(self, baseDir, filename):
        """Returns the possible paths for a dependency filename, for a build
        based in baseDir. Used by getSource."""
        return [
            # We search for [language]-[name] in the libs directory
            os.path.join(baseDir, 'libs', '%s-%s' % (self.lang, filename)),
            # We search for [name] in the libs directory
            os.path.join(baseDir, 'libs', filename)]

    def getSource(self, baseDir, filename):
        """Returns the path for a dependency filename, for a build based in
        baseDir."""
        for path in self._getPossiblePaths(baseDir, filename):
            if os.path.isfile(path):
                return path
        else:
            raise Exception("Dependency not found: `%s` (language: %s)." % (filename, self.lang))

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        """Compile an executable in ownDir, from source files sourceFiles,
        dependencies depFiles."""
        raise Exception("Can't compile files from language %s." % self.lang)

class LanguageC(Language):
    lang = 'c'

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        cmdLine = "/usr/bin/gcc -static -std=gnu99 -O2 -Wall -o %s.exe %s -lm" % (name, ' '.join(sourceFiles))
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguageCpp(Language):
    lang = 'cpp'

    def _getPossiblePaths(self, baseDir, filename):
        return [
            # We search for [language]-[name] in the libs directory
            os.path.join(baseDir, 'libs', '%s-%s' % (self.lang, filename)),
            # For cpp, we also search for c-[name] in the libs directory
            os.path.join(baseDir, 'libs', 'c-%s' % filename),
            # We search for [name] in the libs directory
            os.path.join(baseDir, 'libs', filename)]

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        cmdLine = "/usr/bin/g++ -static -O2 -Wall -o %s.exe %s -lm" % (name, ' '.join(sourceFiles))
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguageCpp11(LanguageCpp):
    lang = 'cpp11'

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        cmdLine = "/usr/bin/g++ -std=gnu++11 -static -O2 -Wall -o %s.exe %s -lm" % (name, ' '.join(sourceFiles))
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguageOcaml(Language):
    lang = 'ocaml'

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        cmdLine = "/usr/bin/ocamlopt -ccopt -static -o %s.exe %s" % (name, ' '.join(sourceFiles))
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguagePascal(Language):
    lang = 'pascal'

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        cmdLine = "/usr/bin/fpc -o%s.exe %s" % (name, ' '.join(sourceFiles))
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguageJava(Language):
    lang = 'java'

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        cmdLine = "/usr/bin/gcj --encoding=utf8 --main=Main -o %s.exe %s" % (name, ' '.join(sourceFiles))
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguageJavascool(LanguageJava):
    lang = 'javascool'

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        # Javascool needs to be transformed before being executed
        cmdLine = "%s %s source.java %s" % (CFG_JAVASCOOLBIN, sourceFiles[0], ' '.join(depFiles))
        Execution(None, compilationParams, cmdLine).execute(ownDir)
        cmdLine = "/usr/bin/gcj --encoding=utf8 --main=Main -o %s.exe source.java" % name
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguageScript(Language):
    lang = 'default-script'

    def _scriptLines(self, sourceFiles, depFiles):
        return map(lambda x: "/bin/sh %s $@\n" % x, sourceFiles)

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        # Scripts are not "compiled", we make an archive out of the source files
        # shar makes a self-extracting "shell archive"
        sharFile = open(os.path.join(ownDir, name + '.exe'), 'w+')
        subprocess.Popen(['shar', '--quiet-unshar', '--quiet'] + sourceFiles + depFiles, stdout=sharFile, cwd=ownDir).wait()
        # We remove the last line of the archive (normally an 'exit 0')
        sharFile.seek(-5, os.SEEK_END)
        pos = sharFile.tell()
        while pos > 0 and sharFile.read(1) != "\n":
            pos -=1
            sharFile.seek(pos, os.SEEK_SET)
        if pos > 0:
            sharFile.truncate(pos + 1)
        # We set the archive to execute the script(s) after self-extracting
        sharFile.writelines(self._scriptLines(sourceFiles, depFiles))
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
        os.chmod(os.path.join(ownDir, name + '.exe'), 493) # chmod 755
        # We build a dummy report
        report = {'timeLimitMs': compilationParams['timeLimitMs'],
                'memoryLimitKb': compilationParams['memoryLimitKb'],
                'commandLine': '[shell script built]',
                'timeTakenMs': 0,
                'realTimeTakenMs': 0,
                'wasKilled': False,
                'wasCached': False,
                'exitCode': 0}

        return report

class LanguageShell(LanguageScript):
    lang = 'sh'

    def _scriptLines(self, sourceFiles, depFiles):
        lines = ["export TASKGRADER_DEPFILES=\"%s\"\n" % ' '.join(depFiles)]
        lines.extend(map(lambda x: "/bin/sh %s $@\n" % x, sourceFiles))
        return lines

class LanguagePython2(LanguageScript):
    lang = 'py2'

    def _getPossiblePaths(self, baseDir, filename):
        return [
            # We search for [language]-[name] in the libs directory
            os.path.join(baseDir, 'libs', '%s-%s' % (self.lang, filename)),
            # For Python langs, we search for run-[name] in the libs directory
            os.path.join(baseDir, 'libs', 'run-%s' % filename),
            # We search for [name] in the libs directory
            os.path.join(baseDir, 'libs', filename)]

    def _scriptLines(self, sourceFiles, depFiles):
        return ["/usr/bin/python2 %s $@\n" % ' '.join(sourceFiles)]

class LanguagePython3(LanguageScript):
    lang = 'py3'

    def _getPossiblePaths(self, baseDir, filename):
        return [
            # We search for [language]-[name] in the libs directory
            os.path.join(baseDir, 'libs', '%s-%s' % (self.lang, filename)),
            # For Python langs, we search for run-[name] in the libs directory
            os.path.join(baseDir, 'libs', 'run-%s' % filename),
            # We search for [name] in the libs directory
            os.path.join(baseDir, 'libs', filename)]

    def _scriptLines(self, sourceFiles, depFiles):
        return ["/usr/bin/python3 %s $@\n" % ' '.join(sourceFiles)]


class Program():
    """Represents a program, from compilation to execution."""

    def __init__(self, compilationDescr, compilationParams, ownDir, baseDir, cache, name='executable'):
        """Create a new Program described by compilationDescr, to be compiled
        in ownDir, with a build based in baseDir and with the cache database
        being cache."""
        self.compilationDescr = compilationDescr
        self.compilationParams = compilationParams
        self.ownDir = ownDir
        self.baseDir = baseDir
        self.name = name
        self.executablePath = os.path.join(self.ownDir, self.name + '.exe')

        self.cacheHandle = cache.getHandle(compilationDescr['files'] + compilationDescr['dependencies'])

        self.compiled = False
        self.triedCompile = False
        self.execution = None

        CFG_LANGUAGES = {'c': LanguageC,
                        'cpp': LanguageCpp,
                        'cpp11': LanguageCpp11,
                        'ml': LanguageOcaml,
                        'ocaml': LanguageOcaml,
                        'java': LanguageJava,
                        'javascool': LanguageJavascool,
                        'sh': LanguageShell,
                        'shell': LanguageShell,
                        'py': LanguagePython3,
                        'py2': LanguagePython2,
                        'py3': LanguagePython3,
                        'python': LanguagePython3,
                        'python2': LanguagePython2,
                        'python3': LanguagePython3}

        try:
            self.language = CFG_LANGUAGES[compilationDescr['language']]()
        except:
            raise Exception("Taskgrader not configured to use language '%s'." % compilationDescr['language'])


    def _getFile(self, fileDescr):
        """Fetch a file contents from a fileDescr object into the Program
        folder. If only the file name is given, getFile will search for a file
        with that name in buildDir, with the language-specific function."""

        # The filename is safe as checked by the JSON schema
        filename = fileDescr['name']
        filepath = os.path.join(self.ownDir, filename)

        if os.path.isfile(filepath):
            # File already exists
            raise Exception("File %s already exists in %s" % (filename, self.ownDir))

        if '/' in filename: # XXX :: ???
            # Need to make a folder
            try:
                os.makedirs(self.ownDir + '/'.join(filename.split('/')[:-1]))
            except:
                pass

        if fileDescr.has_key('content'): # Content given in descr
            open(filepath, 'w').write(fileDescr['content'].encode('utf-8'))
        elif fileDescr.has_key('path'): # Get file by path
            if os.path.isfile(fileDescr['path']):
                symlink(fileDescr['path'], filepath, fromlocal=True)
            else:
                raise Exception("File not found: %s" % fileDescr['path'])
        else: # File is a built dependency
            sourcePath = self.language.getSource(self.baseDir, filename)
            symlink(sourcePath, filepath)

        return filename


    def _compile(self):
        """Effectively compile a program, not using cache (probably because
        there's no cached version).
        It fetches the files as described by the compilationDescr, and uses the
        executionParams as parameters for the compiler execution.
        The resulting file will by named '[name].exe'."""

        compilationDescr = self.compilationDescr
        compilationParams = self.compilationParams

        # We fetch source files into the workingDir
        sourceFiles = map(self._getFile, compilationDescr['files'])

        # We fetch dependencies into the workingDir
        depFiles = map(self._getFile, compilationDescr['dependencies'])

        # We call the language-specific compilation process
        return self.language.compile(self.compilationParams, self.ownDir, sourceFiles, depFiles, self.name)


    def compile(self):
        """Compile the Program, fetching the executable from the cache if possible."""

        if self.compilationParams['useCache']:
            cachef = self.cacheHandle.getCacheFolder('compilation-' + self.name)
            # Check cache
            if cachef.isCached:
                report = cachef.loadReport()
                report['wasCached'] = True
                cachef.loadFiles(self.ownDir)
            else:
                report = self._compile()
                # Make the executable u=rwx,g=rx,a=rx
                cachef.addReport(report)
                if not isExecError(report):
                    os.chmod(self.executablePath, 493)
                    cachef.addFile(self.executablePath, isExecutable=True)
                cachef.save()
        else:
            # We don't use cache at all
            report = self._compile()
            if not isExecError(report):
                os.chmod(self.executablePath, 493)

        self.compiled = not isExecError(report)
        self.triedCompile = True

        return report

    def prepareExecution(self, executionParams):
        """Set the executionParams for the program."""

        if not self.compiled:
            if self.triedCompile:
                raise Exception("Program failed compilation, execution impossible.")
            else:
                raise Exception("Program has not yet been compiled, execution impossible.")
        self.execution = IsolatedExecution(self.executablePath, executionParams, os.path.basename(self.executablePath), language=self.compilationDescr['language'])
        self.executionParams = executionParams

    def execute(self, workingDir, args=None, stdinFile=None, stdoutFile=None, otherInputs=[], outputFiles=[]):
        """Execute the Program in workingDir, with command-line arguments args.
        otherInputs represent the files the Program execution will depend on,
        to differentiate executions in the cache; outputFiles represents the
        output files to save in the cache."""

        if not self.compiled:
            if self.triedCompile:
                raise Exception("Program failed compilation, execution impossible.")
            else:
                raise Exception("Program has not yet been compiled, execution impossible.")
        if not self.execution:
            raise Exception("Execution has not yet been prepared, execution impossible.")

        if self.executionParams['useCache']:
            # Check cache
            inputFiles = []
            inputFiles.extend(otherInputs)
            if stdinFile: inputFiles.append(stdinFile)
            cachef = self.cacheHandle.getCacheFolder('execution-' + self.name, args=args, inputFiles=inputFiles)

            if cachef.isCached:
                # It is cached, we load the report and output files
                report = cachef.loadReport()
                report['wasCached'] = True
                cachef.loadFiles(workingDir)
            else:
                # It is not cached, we execute the program
                report = self.execution.execute(workingDir, args, stdinFile, stdoutFile)
                # Save the report and output files
                cachef.addReport(report)
                if stdoutFile:
                    cachef.addFile(stdoutFile)
                for globPattern in outputFiles:
                    for f in glob.glob(os.path.join(workingDir + globPattern)):
                        cachef.addFile(f)
                cachef.save()
        else:
            # We don't use cache at all
            report = self.execution.execute(workingDir, args, stdinFile, stdoutFile)

        return report


def preprocessJson(json, varData):
    """Preprocess some JSON data, replacing variables with their values.
    There's no checking of the type of values in the variables; the resulting
    JSON is supposed to be checked against a JSON schema.
    varData represents the variable data; all values written as '@varname' in
    the JSON will be replaced by varData['varname']."""
    if (type(json) is str or type(json) is unicode) and len(json) > 0:
        if json[0] == '@':
            # It's a variable, we replace it with the JSON data
            # It will return an error if the variable doesn't exist, it's intended
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
    shutil.copy2(filefrom, fileto)


def isExecError(executionReport):
    """Returns whether an execution returned an error according to its exit code."""
    return (executionReport['exitCode'] != 0)


def capture(path, name='', truncateSize=-1):
    """Capture a file contents for inclusion into the output JSON as a
    captureReport object."""
    if not isInRestrict(path):
        raise Exception("Opening file `%s` for capture is not allowed.")
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


def evaluation(evaluationParams):
    """Full evaluation process."""

    global restrictToPaths

    # Check root path and task path
    # We need to check the keys exist as the JSON schema check is done later
    if not evaluationParams.has_key('rootPath'):
        raise Exception("Input JSON missing 'rootPath' key.")
    if not os.path.isdir(evaluationParams['rootPath']):
        raise Exception("Root path `%s` invalid." % evaluationParams['rootPath'])

    evaluationParams['taskPath'] = evaluationParams['taskPath'].replace('$ROOT_PATH', evaluationParams['rootPath'])

    if not evaluationParams.has_key('taskPath'):
        raise Exception("Input JSON missing 'taskPath' key.")
    if not os.path.isdir(evaluationParams['taskPath']):
        raise Exception("Task path `%s` invalid." % evaluationParams['taskPath'])

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
        varData.update(json.load(open(os.path.join(evaluationParams['taskPath'], 'defaultParams.json'), 'r')))
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
        baseWorkingDir = os.path.join(CFG_BUILDSDIR, evaluationParams['outputPath'])
    else:
        baseWorkingDir = os.path.join(CFG_BUILDSDIR, '_build' + str(random.randint(0, 10000)) + '/')
        while os.path.isdir(baseWorkingDir):
            baseWorkingDir = os.path.join(CFG_BUILDSDIR, '_build' + str(random.randint(0, 10000)) + '/')
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

    cache = CacheDatabase()


    os.mkdir(baseWorkingDir + "libs/")
    os.mkdir(baseWorkingDir + "tests/")

    errorSoFar = False

    # *** Generators
    os.mkdir(baseWorkingDir + "generators/")
    report['generators'] = []
    generators = {}
    for gen in evaluationParams['generators']:
        genDir = "%sgenerators/%s/" % (baseWorkingDir, gen['id'])
        os.mkdir(genDir)
        # We compile the generator
        generator = Program(gen['compilationDescr'], gen['compilationExecution'], genDir, baseWorkingDir, cache, 'generator')
        genReport = generator.compile()
        errorSoFar = errorSoFar or isExecError(genReport)
        report['generators'].append({'id': gen['id'], 'compilationExecution': genReport})
        generators[gen['id']] = generator


    # *** Generations
    os.mkdir(baseWorkingDir + "generations/")
    report['generations'] = []
    for gen in evaluationParams['generations']:
        genDir = "%sgenerations/%s/" % (baseWorkingDir, gen['id'])
        os.mkdir(genDir)

        # Prepare generators
        generator = generators[gen['idGenerator']]
        generator.prepareExecution(gen['genExecution'])
        if gen.has_key('idOutputGenerator'):
            outputGenerator = generators[gen['idOutputGenerator']]
            outputGenerator.prepareExecution(gen['outGenExecution'])

        if gen.has_key('testCases'):
            # We have specific test cases to generate
            for tc in gen['testCases']:
                genReport = {'id': "%s.%s" % (gen['id'], tc['name'])}
                if gen.has_key('idOutputGenerator'):
                    # We also have an output generator, we generate `name`.in and `name`.out
                    genReport['generatorExecution'] = generator.execute(genDir, args=tc['params'], stdoutFile=genDir + tc['name'] + '.in')
                    if not isExecError(genReport['generatorExecution']):
                        filecopy(genDir + tc['name'] + '.in', baseWorkingDir + 'tests/' + tc['name'] + '.in')

                    genReport['outputGeneratorExecution'] = outputGenerator.execute(genDir, args=tc['params'], stdoutFile=genDir + tc['name'] + '.out')
                    if not isExecError(genReport['outputGeneratorExecution']):
                        filecopy(genDir + tc['name'] + '.out', baseWorkingDir + 'tests/' + tc['name'] + '.out')

                    errorSoFar = errorSoFar or isExecError(genReport['generatorExecution']) or isExecError(genReport['outputGeneratorExecution'])
                else:
                    # We only have one generator, we assume `name` is the name of the test file to generate
                    genReport['generatorExecution'] = generator.execute(genDir, args=tc['params'], stdoutFile=genDir + tc['name'])
                    if isExecError(genReport['generatorExecution']):
                        errorSoFar = True
                    else:
                        filecopy(genDir + tc['name'], baseWorkingDir + 'tests/' + tc['name'], fromlocal=True, tolocal=True)
                report['generations'].append(genReport)

        else:
            # We generate the test cases just by executing the generators
            genReport = {'id': gen['id']}
            genReport['generatorExecution'] = generator.execute(genDir,
                outputFiles=['*.in', '*.out', '*.h', '*.java', '*.ml', '*.mli', '*.pas', '*.py'])
            errorSoFar = errorSoFar or isExecError(genReport['generatorExecution'])
            if gen.has_key('idOutputGenerator'):
                # We also have an output generator
                genReport['outputGeneratorExecution'] = outputGenerator.execute(genDir, outputFiles=['*.out'])
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
            filepath = os.path.join(baseWorkingDir, "tests", et['name'])
            if et.has_key('content'): # Content given in descr
                open(filepath, 'w').write(et['content'].encode('utf-8'))
            elif et.has_key('path'): # Get file by path
                if os.path.isfile(et['path']):
                    symlink(et['path'], filepath, fromlocal=True)
                else:
                    raise Exception("File not found: %s" % et['path'])

    # *** Sanitizer
    os.mkdir(baseWorkingDir + "sanitizer/")
    sanitizer = Program(evaluationParams['sanitizer']['compilationDescr'], evaluationParams['sanitizer']['compilationExecution'], baseWorkingDir + "sanitizer/", baseWorkingDir, cache, 'sanitizer')
    report['sanitizer'] = sanitizer.compile()
    sanitizer.prepareExecution(evaluationParams['sanitizer']['runExecution'])
    errorSoFar = errorSoFar or isExecError(report['sanitizer'])

    # *** Checker
    os.mkdir(baseWorkingDir + "checker/")
    checker = Program(evaluationParams['checker']['compilationDescr'], evaluationParams['checker']['compilationExecution'], baseWorkingDir + "checker/", baseWorkingDir, cache, 'checker')
    report['checker'] = checker.compile()
    checker.prepareExecution(evaluationParams['checker']['runExecution'])
    errorSoFar = errorSoFar or isExecError(report['checker'])

    # Did we encounter an error so far?
    if errorSoFar:
        raise Exception("Error in task generation. Please check the partial report for more information:\n%s" % json.dumps(report))


    # *** Solutions
    os.mkdir(baseWorkingDir + "solutions/")
    report['solutions'] = []
    solutions = {} # Language and source files of solutions, need this for the evaluations
    solutionsWithErrors = []
    for sol in evaluationParams['solutions']:
        solDir = "%ssolutions/%s/" % (baseWorkingDir, sol['id'])
        os.mkdir(solDir)
        # We only compile the solution
        solution = Program(sol['compilationDescr'], sol['compilationExecution'],
               solDir, baseWorkingDir, cache, 'solution')
        solReport = solution.compile()
        report['solutions'].append({'id': sol['id'], 'compilationExecution': solReport})
        solutions[sol['id']] = solution
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
        solution = solutions[test['idSolution']]

        mainTestReport = {'name': test['idSolution'], 'testsReports': []}
        testDir = "%sexecutions/%s.%s/" % (baseWorkingDir, test['idSolution'], test['id'])
        os.mkdir(testDir)

        # Prepare solution execution
        solution.prepareExecution(test['runExecution'])

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
            subTestReport['sanitizer'] = sanitizer.execute(testDir, stdinFile=tf)
            if isExecError(subTestReport['sanitizer']):
                # Sanitizer found an error, we skip this file
                mainTestReport['testsReports'].append(subTestReport)
                continue
            # We execute the solution
            filecopy(tf, testDir, fromlocal=True) # Need it for the checker
            subTestReport['execution'] = solution.execute(testDir,
                    stdinFile=testDir + baseTfName + '.in', stdoutFile=testDir + baseTfName + '.solout')
            if isExecError(subTestReport['execution']):
                # Solution returned an error, no need to check
                mainTestReport['testsReports'].append(subTestReport)
                continue
            # We execute the checker
            if os.path.isfile(tf[:-3] + '.out'):
                filecopy(tf[:-3] + '.out', testDir, fromlocal=True)
            else:
                # We write a dummy .out file, the checker probably doesn't need it
                open(testDir + baseTfName + '.out', 'w')
            subTestReport['checker'] = checker.execute(testDir,
                    args="%s.solout %s.in %s.out" % tuple([baseTfName]*3),
                    stdinFile=testDir + baseTfName + '.out',
                    stdoutFile=testDir + baseTfName + '.ok',
                    otherInputs=[testDir + baseTfName + '.in', testDir + baseTfName + '.solout'])
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
    try:
        json.dump(evaluation(inJson), sys.stdout)
    except TemporaryException as err:
        # We use a different return code for TemporaryException
        traceback.print_exc()
        sys.exit(2)
