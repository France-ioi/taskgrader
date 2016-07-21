#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This simple tool manages every step of grading a contest task, from the
# generation of test data to the grading of a solution output.
# See README.md for more information.


import argparse, cPickle, fcntl, glob, hashlib, json, logging, os, platform
import random, shlex, shutil, sqlite3, stat, sys, subprocess, threading, time
import traceback


# Load configuration; default values will be overwritten by user-defined ones
from config_default import *
from config import *

# Handle configuration variables
for var in ['CFG_BASEDIR', 'CFG_BINDIR']:
    if eval(var) == 'CHANGE_ME':
        raise Exception("Configuration variable '%s' not defined.\nPlease edit `config.py`." % var)

# Cannot compile as static on Mac OS X
if CFG_STATIC == 'auto':
    if platform.system() == 'Darwin':
        CFG_STATIC = False
    else:
        CFG_STATIC = True

# Mac OS X doesn't have an appropriate 'time' binary
if CFG_MULTICHECK and CFG_MULTICHECK_LIGHT == 'auto':
    if platform.system() == 'Darwin':
        CFG_MULTICHECK_LIGHT = True
    else:
        CFG_MULTICHECK_LIGHT = False


SELFDIR = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
# Add taskgrader dir to ENV
os.environ["TASKGRADERDIR"] = SELFDIR

RESTRICT_PATHS = []

sys.path.append(CFG_JSONSCHEMA)
try:
    from jsonschema import validate
except:
    validate = None


class TemporaryException(Exception):
    """TemporaryException is a special exception representing a temporary
    error, for which reexecuting the exact same evaluation can succeed at a
    later time."""

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class UnsupportedLanguage(Exception):
    """UnsupportedLanguage is a special exception for when the evaluation needs
    a language which is not supported by the taskgrader (either because the
    taskgrader doesn't know the language or lacks a dependency)."""

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
        logging.debug("Opening CacheFolder #%d." % cacheId)

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
            # Write in cache.ok the last access timestamp
            try:
                open(self._makePath('cache.ok'), 'w').write(str(time.time()))
            except:
                pass
            logging.debug("CacheFolder #%d is cached, files: %s." % (cacheId, ', '.join(self.files)))
        else:
            logging.debug("CacheFolder #%d is not cached." % cacheId)


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
        logging.info("Invalidating CacheFolder #%d" % self.cacheId)
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
        logging.debug("Adding file `%s` to CacheFolder #%d" % (path, self.cacheId))
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

        logging.debug("Adding report to CacheFolder #%d" % self.cacheId)
        json.dump(data, open(self._makePath('report.json'), 'w'))

    def save(self):
        """Save the cache, marking it as complete and usable."""
        logging.debug("Saving CacheFolder #%d, files: %s" % (self.cacheId, ', '.join(self.files)))
        cPickle.dump(self.files, open(self._makePath('cache.files'), 'w'))
        open(self._makePath('cache.ok'), 'w').write(' ')
        self.isCached = True

    def loadFiles(self, path):
        """Load files from the cache into the folder path. Will behave as if
        the execution took place in that folder."""
        if not self.isCached:
            raise Execption("Tried to load non-cached files from cache (ID %d)." % self.cacheId)

        logging.debug("Loading CacheFolder #%d into folder `%s`" % (self.cacheId, path))
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
            if fileDescr.has_key('path') and fileDescr['path'] != '':
                # File path is given, we use the path as reference
                filePath = os.path.abspath(os.path.realpath(fileDescr['path']))
                md5sum = hashlib.md5(open(filePath, 'rb').read()).hexdigest()
                fileIdList.append("path:%s" % filePath)
                fileHashList.append(md5sum)
            elif fileDescr.has_key('content'):
                # File content is given, we use the name given and the hash as reference
                md5sum = hashlib.md5(fileDescr['content'].encode('utf-8', errors='ignore')).hexdigest()
                fileIdList.append("file:%s:%s" % (fileDescr['name'], md5sum))
            else:
                # It's a local dependency
                fileIdList.append("local:%s" % fileDescr['name'])

        fileIdList.sort()
        fileHashList.sort() # Both lists won't be sorted the same but it's not an issue

        self.programId = "program:%s" % (';'.join(fileIdList))
        self.programHashes = ';'.join(fileHashList)

        logging.debug("New CacheHandle, programId `%s`" % self.programId)


    def getCacheFolder(self, cacheType, args='', execParams=None, inputFiles=[]):
        """Returns the CacheFolder for the program executed with args and
        inputFiles as input.
        cacheType represents the type of cache (compilation, execution); it
        must be the same string among all executions of the program."""

        # We add an identifier for execution limits
        # TODO :: add identifiers for all executionParams?
        params = ''
        if execParams:
            params = 'timelimit:%s;memlimit:%s' % (execParams['timeLimitMs'], execParams['memoryLimitKb'])
        else:
            params = ''

        inputIdList = []
        # We add identifiers for input files (local name and md5sum)
        for f in inputFiles:
            md5sum = hashlib.md5(open(f, 'rb').read()).hexdigest()
            inputIdList.append("input:%s:%s" % (os.path.basename(f), md5sum))

        # This will be the ID string in the database, containing the cache type and the input files list
        filesId = "%s;cache:%s;args:%s;%s;%s" % (self.programId, cacheType, args, params, ";".join(inputIdList))

        logging.debug("Getting CacheFolder for filesId `%s`" % filesId)

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
            logging.debug("Added new entry into cache database")
            self.database.commit()
            newId = dbCur.lastrowid
            return CacheFolder(newId)


class CacheDatabase():
    """Represents the cache database."""

    def _loadDatabase(self):
        """Load the database."""
        self.database = sqlite3.connect(CFG_CACHEDBPATH)
        self.database.row_factory = sqlite3.Row

    def __init__(self):
        self._loadDatabase()
        # Recreate cache table if it was deleted for some reason
        try:
            self.database.execute("SELECT 1 FROM cache WHERE 1=1")
        except:
            logging.warning("Cache database was corrupted, resetting...")
            self.database.close()
            self.database = None
            resetProc = subprocess.Popen([CFG_RESET_SCRIPT])
            resetProc.wait()
            self._loadDatabase()

    def getHandle(self, files):
        return CacheHandle(self.database, files)


def getFile(fileDescr, destDir, errorFatal=True, language=None, baseDir=None):
    """Fetch a file into folder destDir. If no path nor content is given,
    search for it as a dependency for the language in baseDir."""
    # The filename is safe as checked by the JSON schema
    filename = fileDescr['name']
    filepath = os.path.join(destDir, filename)

    if os.path.isfile(filepath):
        # File already exists
        if errorFatal:
            raise Exception("File %s already exists in %s" % (filename, destDir))
        else:
            return filename

    if '/' in filename:
        # Need to make a folder
        try:
            os.makedirs(os.path.join(destDir, os.path.dirname(filename)))
        except:
            pass

    if fileDescr.has_key('path') and fileDescr['path'] != '': # Get file by path
        if os.path.isfile(fileDescr['path']):
            symlink(fileDescr['path'], filepath, fromlocal=True)
        elif errorFatal:
            raise Exception("File not found: `%s`" % fileDescr['path'])
    elif fileDescr.has_key('content'): # Content given in descr
        open(filepath, 'w').write(fileDescr['content'].encode('utf-8'))
    elif language and baseDir: # File is a built dependency
        sourcePath = language.getSource(baseDir, filename, errorFatal=errorFatal)
        if sourcePath:
            symlink(sourcePath, filepath)

    return filename


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

        # Copy values from arguments
        self.baseReport = {'timeLimitMs': self.executionParams['timeLimitMs'],
            'memoryLimitKb': self.executionParams['memoryLimitKb'],
            'wasCached': False,
            'realMemoryLimitKb': self.realMemoryLimitKb,
            'realTimeLimitMs': self.realTimeLimit}
        if 'continueOnError' in self.executionParams:
            self.baseReport['continueOnError'] = self.executionParams['continueOnError']

        logging.debug("New Execution initialized for executable `%s`, cmd `%s`" % (executablePath, cmd))


    def _prepareExecute(self, workingDir, stdinFile=None, stdoutFile=None):
        """Prepares the execution in workingDir, checks stdinFile and
        stdoutFile paths."""

        # Copy executable to workingDir
        if self.executablePath:
            deployPath = os.path.join(workingDir, os.path.basename(self.executablePath))
            if os.path.islink(deployPath):
                try:
                    os.unlink(deployPath)
                except:
                    pass
            try:
                symlink(self.executablePath, deployPath)
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

        # Add files from executionParams/addFiles
        for fileDescr in self.executionParams.get('addFiles', []):
            getFile(fileDescr, workingDir, errorFatal=False)


    def _doExecute(self, workingDir, args=None):
        """Executes the command in workingDir with args."""

        cmdLine = self.cmd + ((' ' + args) if args else '')

        # Open stdin file
        stdinHandle = (open(self.stdinFile, 'rb') if self.stdinFile else None)

        stderrFile = os.path.join(workingDir, 'stderr')

        proc = subprocess.Popen(shlex.split(cmdLine), stdin=stdinHandle, stdout=open(self.stdoutFile, 'w'),
                stderr=open(stderrFile, 'w'), cwd=workingDir)
        # We allow a wall time of 3 times the timeLimit
        waitWithTimeout(proc, (1+int(self.executionParams['timeLimitMs']/1000))*3)

        # Make execution report
        report = {}
        report.update(self.baseReport)
        report.update({
                'commandLine': cmdLine,
                'timeTakenMs': -1, # We don't know
                'realTimeTakenMs': -1, # We don't know
                'wasKilled': False,
                'exitCode': proc.returncode,
                'exitSig': -1 # We don't know
            })

        report['stdout'] = capture(self.stdoutFile, name='stdout',
                truncateSize=self.executionParams['stdoutTruncateKb'] * 1024)
        report['stderr'] = capture(stderrFile, name='stderr',
                truncateSize=self.executionParams['stderrTruncateKb'] * 1024)

        filesReports = []
        for f in globOfGlobs(workingDir, self.executionParams['getFiles']):
            filesReports.append(capture(f, name=os.path.basename(f)))
        report['files'] = filesReports

        return report


    def execute(self, workingDir, args=None, stdinFile=None, stdoutFile=None):
        """Execute the program in workingDir, with command-line arguments args,
        and standard input and output redirected from stdinFile and to
        stdoutFile."""
        logging.info("Executing executable `%s`, cmd `%s`, args `%s` in dir `%s`" % (self.executablePath, self.cmd, args, workingDir))
        self.workingDir = workingDir
        self._prepareExecute(workingDir, stdinFile, stdoutFile)
        return self._doExecute(workingDir, args)


class IsolatedExecution(Execution):
    """Represents an execution encapsulated in isolate."""

    def _doExecute(self, workingDir, args=None):
        # Check isolate is present
        if not os.path.isfile(CFG_ISOLATEBIN) or (os.stat(CFG_ISOLATEBIN).st_mode & stat.S_ISUID) == 0:
            logging.warning("Isolate is not properly configured, falling back to normal execution. Check documentation for more information.")
            return Execution._doExecute(self, workingDir, args=args)
        if not os.path.isfile(CFG_RIGHTSBIN) or (os.stat(CFG_RIGHTSBIN).st_mode & stat.S_ISUID) == 0:
            logging.warning("Box-rights for isolate is not properly configured, falling back to normal execution. Check documentation for more information.")
            return Execution._doExecute(self, workingDir, args=args)

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
        (isolateDir, isolateErr) = communicateWithTimeout(initProc, 10)

        if initProc.returncode != 0:
            raise Exception("Error while initializing isolate box (#%d)." % initProc.returncode)

        # isolatePath will be the path of the sandbox, as given by isolate
        isolateDir = os.path.join(isolateDir.strip(), 'box/')

        # Build isolate command line
        isolatedCmdLine  = CFG_ISOLATEBIN
        isolatedCmdLine += ' --processes'
        isolatedCmdLine += ' --env=HOME --env=PATH'
        isolatedCmdLine += ' --meta=%s' % os.path.join(workingDir, 'isolate.meta')
        # Add access to some folders
        for folder in CFG_ISOLATE_AVAILABLE:
            isolatedCmdLine += ' --dir="%s":maybe' % folder
        # Use an unique box ID
        isolatedCmdLine += ' --box-id=%d' % boxId
        if self.executionParams['timeLimitMs'] > 0:
            isolatedCmdLine += ' --time=' + str(self.realTimeLimit / 1000.)
            isolatedCmdLine += ' --wall-time=' + str(3 * self.realTimeLimit / 1000.)
        if self.executionParams['memoryLimitKb'] > 0:
            if CFG_CONTROLGROUPS:
                isolatedCmdLine += ' --cg-mem=' + str(self.realMemoryLimitKb)
            else:
                isolatedCmdLine += ' --mem=' + str(self.realMemoryLimitKb)
        if self.stdinFile:
            filecopy(self.stdinFile, os.path.join(workingDir, 'isolated.stdin'), fromlocal=True)
            isolatedCmdLine += ' --stdin=isolated.stdin'
        if CFG_CONTROLGROUPS:
            isolatedCmdLine += ' --cg --cg-timing'
        isolatedCmdLine += ' --stdout=isolated.stdout --stderr=isolated.stderr'
        isolatedCmdLine += ' --run -- ' + cmdLine

        # Clean old isolate files
        for f in ['isolated.stdout', 'isolated.stderr', 'isolated.meta']:
            try:
                os.unlink(os.path.join(workingDir, f))
            except:
                pass

        # Copy files from working directory to sandbox
        dircopy(workingDir, isolateDir)

        # Create meta file with right owner/permissions
        open(os.path.join(workingDir, 'isolate.meta'), 'w')

        logging.debug("Executing isolate: `%s`" % isolatedCmdLine)

        # Execute the isolated program
        proc = subprocess.Popen(shlex.split(isolatedCmdLine), cwd=workingDir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (procOut, procErr) = communicateWithTimeout(proc, int(10 + 3 * self.realTimeLimit / 1000.))

        # Get metadata from isolate execution
        isolateMeta = {}
        try:
            for l in open(os.path.join(workingDir, 'isolate.meta'), 'r').readlines():
                [name, val] = l.split(':', 1)
                isolateMeta[name] = val.strip()
        except:
            pass

        if proc.returncode > 1:
            # Isolate error (0 and 1 refer to the program inside the sandbox)
            # Try to cleanup sandbox
            cleanProc = subprocess.Popen([CFG_ISOLATEBIN, '--cleanup', '--box-id=%d' % boxId], cwd=workingDir)
            waitWithTimeout(cleanProc, 10)
            raise Exception("""Internal isolate error, please check installation: #%d %s
                    while trying to execute `%s` in folder `%s`.
                    stdout: %s
                    stderr: %s""" % (proc.returncode, isolateMeta.get('status', ''),
                                    cmdLine, workingDir,
                                    procOut, procErr))

        # Set file rights so that we can access the files
        rightsProc = subprocess.Popen([CFG_RIGHTSBIN])
        waitWithTimeout(rightsProc, 30)

        # Copy back the files from sandbox
        dircopy(isolateDir, workingDir, overwrite=False)
        filecopy(os.path.join(isolateDir, 'isolated.stdout'), self.stdoutFile)

        # Generate execution report
        if isolateMeta.has_key('time'):
            report['realTimeTakenMs'] = int(float(isolateMeta['time'])*1000)
            report['timeTakenMs'] = int(self.timeUntransform(report['realTimeTakenMs']))
        else:
            report['realTimeTakenMs'] = -1
            report['timeTakenMs'] = -1
        # Memory used: cg-mem is only available when control groups are
        # enabled, and max-rss can be slightly inaccurate
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

        report['stdout'] = capture(os.path.join(workingDir, 'isolated.stdout'), name='stdout',
                truncateSize=self.executionParams['stdoutTruncateKb'] * 1024)
        report['stderr'] = capture(os.path.join(workingDir, 'isolated.stderr'), name='stderr',
                truncateSize=self.executionParams['stderrTruncateKb'] * 1024)

        # Cleanup sandbox
        cleanProc = subprocess.Popen([CFG_ISOLATEBIN, '--cleanup'] + isolateCommonOpts, cwd=workingDir)
        waitWithTimeout(cleanProc, 10)

        return report


def which(name):
    """Searches for a program in PATH."""
    def is_exe(path):
        return os.path.isfile(path) and os.access(path, os.X_OK)

    fpath, basename = os.path.split(name)
    if fpath and is_exe(name):
        return name
    else:
        for spath in os.environ['PATH'].split(os.pathsep):
            spath = spath.strip('"')
            fullpath = os.path.join(spath, name)
            if is_exe(os.path.join(spath, name)):
                return fullpath
    return False


class Language():
    """Represents a language, gives functions for aspects specific to each
    language."""

    lang = 'default'
    # The dependencies will be searched for, if one is not found, the Language
    # will raise an exception in __init__.
    # The full path of each dependency will be stored in self.deppaths; note
    # that this full path is then used by code, so always add additional
    # dependencies at the end of the list.
    dependencies = []

    def __init__(self):
        """Class initialization: check the required dependencies are present."""
        self.deppaths = []
        for f in self.dependencies:
            deppath = which(f)
            if not deppath:
                raise UnsupportedLanguage("Cannot use language '%s', dependency `%s` missing." % (self.lang, f))
            self.deppaths.append(deppath)

    def _getPossiblePaths(self, baseDir, filename):
        """Returns the possible paths for a dependency filename, for a build
        based in baseDir. Used by getSource."""
        return [
            # We search for [language]-[name] in the libs directory
            os.path.join(baseDir, 'libs', '%s-%s' % (self.lang, filename)),
            # We search for [name] in the libs directory
            os.path.join(baseDir, 'libs', filename)]

    def getSource(self, baseDir, filename, errorFatal=True):
        """Returns the path for a dependency filename, for a build based in
        baseDir."""
        for path in self._getPossiblePaths(baseDir, filename):
            if os.path.isfile(path):
                return path
        else:
            if errorFatal:
                raise Exception("Dependency not found: `%s` (language: %s)." % (filename, self.lang))
            else:
                return None

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        """Compile an executable in ownDir, from source files sourceFiles,
        dependencies depFiles."""
        raise Exception("Can't compile files from language %s." % self.lang)

class LanguageC(Language):
    lang = 'c'
    dependencies = ["gcc"]

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        # Add non-header dependencies to compilation
        compFiles = sourceFiles[:]
        compFiles.extend(filter(lambda d: d[-2:] != '.h', depFiles))

        if CFG_STATIC:
            cmdLine = "%s -static -std=gnu99 -O2 -Wall -o %s.exe %s -lm" % (self.deppaths[0], name, ' '.join(compFiles))
        else:
            cmdLine = "%s -std=gnu99 -O2 -Wall -o %s.exe %s -lm" % (self.deppaths[0], name, ' '.join(compFiles))
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguageCpp(Language):
    lang = 'cpp'
    dependencies = ["g++"]

    def _getPossiblePaths(self, baseDir, filename):
        return [
            # We search for [language]-[name] in the libs directory
            os.path.join(baseDir, 'libs', '%s-%s' % (self.lang, filename)),
            # For cpp, we also search for c-[name] in the libs directory
            os.path.join(baseDir, 'libs', 'c-%s' % filename),
            # We search for [name] in the libs directory
            os.path.join(baseDir, 'libs', filename)]

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        # Add non-header dependencies to compilation
        compFiles = sourceFiles[:]
        compFiles.extend(filter(lambda d: d[-2:] != '.h', depFiles))

        if CFG_STATIC:
            cmdLine = "%s -static -O2 -Wall -o %s.exe %s -lm" % (self.deppaths[0], name, ' '.join(compFiles))
        else:
            cmdLine = "%s -O2 -Wall -o %s.exe %s -lm" % (self.deppaths[0], name, ' '.join(compFiles))
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguageCpp11(LanguageCpp):
    lang = 'cpp11'
    dependencies = ["g++"]

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        # Add non-header dependencies to compilation
        compFiles = sourceFiles[:]
        compFiles.extend(filter(lambda d: d[-2:] != '.h', depFiles))

        if CFG_STATIC:
            cmdLine = "%s -std=gnu++11 -static -O2 -Wall -o %s.exe %s -lm" % (self.deppaths[0], name, ' '.join(compFiles))
        else:
            cmdLine = "%s -std=gnu++11 -O2 -Wall -o %s.exe %s -lm" % (self.deppaths[0], name, ' '.join(compFiles))
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguageOcaml(Language):
    lang = 'ocaml'
    dependencies = ["ocamlopt"]

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        if CFG_STATIC:
            cmdLine = "%s -ccopt -static -o %s.exe %s" % (self.deppaths[0], name, ' '.join(sourceFiles))
        else:
            cmdLine = "%s -o %s.exe %s" % (self.deppaths[0], name, ' '.join(sourceFiles))
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguagePascal(Language):
    lang = 'pascal'
    dependencies = ["fpc"]

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        cmdLine = "%s -o%s.exe %s" % (self.deppaths[0], name, ' '.join(sourceFiles))
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguageJava(Language):
    lang = 'java'
    dependencies = ["gcj"]

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        cmdLine = "%s --encoding=utf8 --main=Main -o %s.exe %s" % (self.deppaths[0], name, ' '.join(sourceFiles))
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguageJavascool(LanguageJava):
    lang = 'javascool'
    dependencies = ["gcj", CFG_JAVASCOOLBIN]

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        # Javascool needs to be transformed before being executed
        cmdLine = "%s %s source.java %s" % (CFG_JAVASCOOLBIN, sourceFiles[0], ' '.join(depFiles))
        Execution(None, compilationParams, cmdLine).execute(ownDir)
        cmdLine = "%s --encoding=utf8 --main=Main -o %s.exe source.java" % (self.deppaths[0], name)
        return Execution(None, compilationParams, cmdLine).execute(ownDir)

class LanguageScript(Language):
    lang = 'default-script'
    dependencies = ["openssl"]

    def _scriptLines(self, sourceFiles, depFiles):
        """Returns the commands to execute the program when there are multiple
        sourceFiles and depFiles. Added at the end of the self-extracting
        archive (for language classes derived from LanguageScript)."""
        return map(lambda x: "/bin/sh %s $@\n" % x, sourceFiles)

    def _singleScriptShebang(self):
        """Return the shebang to add to the start of the script; used when
        there is only one sourceFile and no depFile."""
        return "#!/bin/sh"

    def compile(self, compilationParams, ownDir, sourceFiles, depFiles, name='executable'):
        if len(sourceFiles) == 1 and len(depFiles) == 0:
            # Only one file, the executable is the script itself
            execPath = os.path.join(ownDir, name + '.exe')
            execFile = open(execPath, 'w')
            # We add a shebang (even if the script already has one)
            execFile.write(self._singleScriptShebang())
            execFile.write("\n")

            # Read the source script
            source = open(os.path.join(ownDir, sourceFiles[0]), 'r')
            sourceFirstLine = source.readline()
            # Check whether first line of the script is a shebang; in that case, remove it
            if sourceFirstLine[:2] != '#!':
                execFile.write(sourceFirstLine)
            # Copy the rest of the script
            execFile.write(source.read())

            execFile.close()
            # We set the executable bits
            os.chmod(execPath, 493) # chmod 755
        else:
            # Multiple files, we write a shell archive which extracts all
            # source files and dependencies, then executes the scripts
            sharPath = os.path.join(ownDir, name + '.exe')
            sharFile = open(sharPath, 'w')
            sharFile.write("#!/bin/sh\n")
            for f in (sourceFiles + depFiles):
                # Encode each file in base64, use openssl to extract them
                sharFile.write("%s base64 -d -out \"%s\" 2> /dev/null <<EOF\n" % (self.deppaths[0], f))
                sharFile.write(open(os.path.join(ownDir, f), 'r').read().encode("base64"))
                sharFile.write("EOF\n")
            # Execute the script(s) after self-extracting
            sharFile.writelines(self._scriptLines(sourceFiles, depFiles))
            sharFile.close()
            # We set the archive executable bits
            os.chmod(sharPath, 493) # chmod 755

        # We build a dummy report for this "compilation"
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
    dependencies = ["openssl"]

    def _scriptLines(self, sourceFiles, depFiles):
        lines = [
            "export TASKGRADER_DEPFILES=\"%s\"\n" % ' '.join(depFiles),
            "export TASKGRADERDIR=\"%s\"\n" % SELFDIR,
            ]
        lines.extend(map(lambda x: "/bin/sh %s $@\n" % x, sourceFiles))
        return lines

    def _singleScriptShebang(self):
        return "#!/bin/sh"

class LanguageNodejs(LanguageScript):
    lang = 'js'
    dependencies = ["openssl", "nodejs"]

    def _scriptLines(self, sourceFiles, depFiles):
        # TODO :: try to configure nodejs to use less memory
        return map(lambda x: "%s %s $@\n" % (self.deppaths[1], x), sourceFiles)

    def _singleScriptShebang(self):
        return "#!%s" % self.deppaths[1]

class LanguagePhp(LanguageScript):
    lang = 'php'
    dependencies = ["openssl", "php5"]

    def _scriptLines(self, sourceFiles, depFiles):
        return map(lambda x: "%s --file %s $@\n" % (self.deppaths[1], x), sourceFiles)

    def _singleScriptShebang(self):
        return "#!%s" % self.deppaths[1]

class LanguagePython2(LanguageScript):
    lang = 'py2'
    dependencies = ["openssl", "python2.7"]

    def _getPossiblePaths(self, baseDir, filename):
        return [
            # We search for [language]-[name] in the libs directory
            os.path.join(baseDir, 'libs', '%s-%s' % (self.lang, filename)),
            # For Python langs, we search for run-[name] in the libs directory
            os.path.join(baseDir, 'libs', 'run-%s' % filename),
            # We search for [name] in the libs directory
            os.path.join(baseDir, 'libs', filename)]

    def _scriptLines(self, sourceFiles, depFiles):
        return ["%s %s $@\n" % (self.deppaths[1], ' '.join(sourceFiles))]

    def _singleScriptShebang(self):
        return "#!%s" % self.deppaths[1]

class LanguagePython3(LanguageScript):
    lang = 'py3'
    dependencies = ["openssl", "python3"]

    def _getPossiblePaths(self, baseDir, filename):
        return [
            # We search for [language]-[name] in the libs directory
            os.path.join(baseDir, 'libs', '%s-%s' % (self.lang, filename)),
            # For Python langs, we search for run-[name] in the libs directory
            os.path.join(baseDir, 'libs', 'run-%s' % filename),
            # We search for [name] in the libs directory
            os.path.join(baseDir, 'libs', filename)]

    def _scriptLines(self, sourceFiles, depFiles):
        return ["%s %s $@\n" % (self.deppaths[1], ' '.join(sourceFiles))]

    def _singleScriptShebang(self):
        return "#!%s" % self.deppaths[1]


class Program():
    """Represents a program, from compilation to execution."""

    def __init__(self, compilationDescr, compilationParams, ownDir, baseDir, cache, name='executable'):
        """Create a new Program described by compilationDescr, to be compiled
        in ownDir, with a build based in baseDir and with the cache database
        being cache."""
        logging.info("Creating new Program `%s` in dir `%s`" % (name, ownDir))
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

        # Check whether execution should be isolated
        self.isolate = True
        for f in compilationDescr['files']:
            if 'path' in f and f['path'] != '':
                fPath = os.path.abspath(f['path'])
                if fPath in CFG_NOISOLATE:
                    self.isolate = False
        logging.info("Program will%s be isolated." % ('' if self.isolate else ' not'))

        # TODO :: move languages into libraries
        CFG_LANGUAGES = {
            'c': LanguageC,
            'cpp': LanguageCpp,
            'cpp11': LanguageCpp11,
            'ml': LanguageOcaml,
            'ocaml': LanguageOcaml,
            'java': LanguageJava,
            'javascool': LanguageJavascool,
            'js': LanguageNodejs,
            'sh': LanguageShell,
            'shell': LanguageShell,
            'pascal': LanguagePascal,
            'php': LanguagePhp,
            'py': LanguagePython2,
            'py2': LanguagePython2,
            'py3': LanguagePython3,
            'python': LanguagePython2,
            'python2': LanguagePython2,
            'python3': LanguagePython3}

        if CFG_LANGUAGES.has_key(compilationDescr['language']):
            self.language = CFG_LANGUAGES[compilationDescr['language']]()
        else:
            raise UnsupportedLanguage("Taskgrader not configured to use language '%s'." % compilationDescr['language'])


    def _getFile(self, fileDescr):
        """Fetch a file contents from a fileDescr object into the Program
        folder. If only the file name is given, getFile will search for a file
        with that name in buildDir, with the language-specific function."""
        return getFile(fileDescr, self.ownDir, errorFatal=True, language=self.language, baseDir=self.baseDir)

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

        # We call the language-specific compilation process
        report = self.language.compile(self.compilationParams, self.ownDir, sourceFiles, depFiles, self.name)

        if isExecError(report, checkContinue=False) and self.compilationParams.get('continueOnError', False):
            # Compilation didn't succeed but the continueOnError flag is set
            # We write a dummy executable which just exits with code 1
            open(self.executablePath, 'w').write("#!/bin/sh\nexit 1\n")
            os.chmod(self.executablePath, 493)

        return report


    def compile(self):
        """Compile the Program, fetching the executable from the cache if possible."""

        logging.info("Compiling Program `%s`" % self.name)

        if self.compilationParams['useCache']:
            cachef = self.cacheHandle.getCacheFolder('compilation-%s-%s' % (self.compilationDescr['language'], self.name), execParams=self.compilationParams)
            # Check cache
            if cachef.isCached:
                logging.debug("Compiled version was cached")
                report = cachef.loadReport()
                report['wasCached'] = True
                cachef.loadFiles(self.ownDir)
            else:
                logging.debug("No cached version")
                report = self._compile()
                cachef.addReport(report)
                if not isExecError(report):
                    # Make the executable u=rwx,g=rx,a=rx
                    os.chmod(self.executablePath, 493)
                    for f in [self.name + '.exe', 'stdout', 'stderr']:
                        if os.path.isfile(os.path.join(self.ownDir, f)):
                            cachef.addFile(os.path.join(self.ownDir, f), isExecutable=True)
                cachef.save()
        else:
            # We don't use cache at all
            logging.debug("Not using cache")
            report = self._compile()
            if not isExecError(report):
                os.chmod(self.executablePath, 493)

        self.compiled = not isExecError(report)
        self.triedCompile = True

        if isExecError(report):
            logging.info("Compilation failed.")
        else:
            logging.info("Compilation successful.")

        return report

    def prepareExecution(self, executionParams):
        """Set the executionParams for the program."""

        if not self.compiled:
            if self.triedCompile:
                raise Exception("Program failed compilation, execution impossible.")
            else:
                raise Exception("Program has not yet been compiled, execution impossible.")

        if self.isolate:
            self.execution = IsolatedExecution(self.executablePath, executionParams, './%s' % os.path.basename(self.executablePath), language=self.compilationDescr['language'])
        else:
            self.execution = Execution(self.executablePath, executionParams, './%s' % os.path.basename(self.executablePath), language=self.compilationDescr['language'])
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

        logging.info("Executing Program `%s`, args `%s`, in dir `%s`" % (self.name, args, workingDir))

        if self.executionParams['useCache']:
            # Check cache
            inputFiles = []
            inputFiles.extend(otherInputs)
            if stdinFile: inputFiles.append(stdinFile)
            cachef = self.cacheHandle.getCacheFolder('execution-%s-%s' % (self.compilationDescr['language'], self.name), args=args, execParams=self.executionParams, inputFiles=inputFiles)

            if cachef.isCached:
                # It is cached, we load the report and output files
                logging.debug("Version in cache")
                report = cachef.loadReport()
                report['wasCached'] = True
                cachef.loadFiles(workingDir)
            else:
                logging.debug("No version in cache")
                # It is not cached, we execute the program
                report = self.execution.execute(workingDir, args, stdinFile, stdoutFile)
                # Save the report and output files
                cachef.addReport(report)
                if stdoutFile:
                    cachef.addFile(stdoutFile)
                for f in globOfGlobs(workingDir, outputFiles):
                    cachef.addFile(f)
                cachef.save()
        else:
            # We don't use cache at all
            logging.debug("Not using cache")
            report = self.execution.execute(workingDir, args, stdinFile, stdoutFile)

        if isExecError(report):
            logging.info("Execution failed.")
        else:
            logging.info("Execution successful.")

        return report


def multiChecker(workingDir, checkList, checker, executionParams):
    """Do multiple checks in the same isolated execution."""
    if len(checkList) == 0:
        return []

    # Find time executable if present
    if CFG_MULTICHECK_LIGHT:
        timePath = None
    else:
        timePath = which('time')

    # Make execution params for the multi-execution
    multiExecParams = {}
    multiExecParams.update(executionParams)
    multiExecParams['timeLimitMs'] = min(CFG_MAX_TIMELIMIT, executionParams['timeLimitMs'] * len(checkList))

    # Build the script
    mcPath = os.path.join(workingDir, 'multichecker.sh')
    mcFile = open(mcPath, 'w')
    mcFile.write("#!/bin/sh\n")

    # Add all tests
    cmdLines = {}
    for (i, tf) in checkList:
        # Make checker command-line
        baseCmdLine = "%(checker)s %(testFile)s.solout %(testFile)s.in %(testFile)s.out"
        baseCmdLine = baseCmdLine % {'testFile': tf,
            'checker': './%s' % os.path.basename(checker.executablePath)}
        cmdLines[i] = baseCmdLine

        if timePath:
            # Use time for execution statistics
            cmdLine = '%(time)s --output %(testFile)s.time --format "%%x %%M %%U" '
        else:
            cmdLine = ''
        # Execute the checker
        cmdLine += baseCmdLine
        # Redirect output
        cmdLine += " > %(testFile)s.cout 2> %(testFile)s.cerr"
        # Replace variables
        cmdLine = cmdLine % {'time': timePath,
            'testFile': tf}
        mcFile.write(cmdLine + "\n")
        if not timePath:
            # If we don't use time, we ask sh to write the exit code
            mcFile.write("echo $? > %s.code\n" % tf)

    mcFile.close()
    os.chmod(mcPath, 493) # chmod 755

    # Execute the script
    if checker.isolate:
        report = IsolatedExecution(checker.executablePath, multiExecParams, './multichecker.sh').execute(workingDir)
    else:
        report = Execution(checker.executablePath, multiExecParams, './multichecker.sh').execute(workingDir)

    # Build reports
    # Many elements aren't present in the reports from a multi-check
    baseReport = {
        'timeLimitMs': multiExecParams['timeLimitMs'],
        'memoryLimitKb': multiExecParams['memoryLimitKb'],
        'realMemoryLimitKb': -1,
        'realTimeLimitMs': -1,
        'wasCached': False,
        'wasKilled': False,
        'exitSig': -1}

    filesReports = []
    for f in globOfGlobs(workingDir, executionParams['getFiles']):
        filesReports.append(capture(f, name=os.path.basename(f)))
    baseReport['files'] = filesReports

    allReports = []

    # Make the report for each check
    for (i, tf) in checkList:
        report = {}
        report.update(baseReport)
        report['commandLine'] = cmdLines[i]

        if timePath:
            # Fetch time statistics
            timeFile = open(os.path.join(workingDir, '%s.time' % tf), 'r')
            timeStats = timeFile.read().strip().split()[-3:]
            report.update({
                'exitCode': int(timeStats[0]),
                'memoryUsedKb': int(timeStats[1]),
                'timeTakenMs': int(float(timeStats[2])*1000),
                'realTimeTakenMs': int(float(timeStats[2])*1000)})
        else:
            exitFile = open(os.path.join(workingDir, '%s.code' % tf), 'r')
            report.update({
                'exitCode': int(exitFile.read().strip()),
                'memoryUsedKb': -1,
                'timeTakenMs': -1,
                'realTimeTakenMs': -1})

        report['stdout'] = capture(os.path.join(workingDir, '%s.cout' % tf),
            name='stdout',
            truncateSize=multiExecParams['stdoutTruncateKb'] * 1024)
        report['stderr'] = capture(os.path.join(workingDir, '%s.cerr' % tf),
            name='stderr',
            truncateSize=multiExecParams['stderrTruncateKb'] * 1024)

        allReports.append((i, report))

    return allReports


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
                raise Exception("varData doesn't have key `%s`, keys of varData:\n%s" % (varName, str(varData.keys())))
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


def waitWithTimeout(subProc, timeout=0):
    """Waits for subProc completion or timeout seconds, whichever comes
    first."""
    if timeout > 0:
        to = threading.Timer(timeout, subProc.kill)
        try:
            to.start()
            subProc.wait()
        finally:
            to.cancel()
    else:
        subProc.wait()


def communicateWithTimeout(subProc, timeout=0, input=None):
    """Communicates with subProc until its completion or timeout seconds,
    whichever comes first."""
    if timeout > 0:
        to = threading.Timer(timeout, subProc.kill)
        try:
            to.start()
            return subProc.communicate(input=input)
        finally:
            to.cancel()
    else:
        return subProc.communicate(input=input)


def isInRestrict(path):
    """Check whether a path is in the allowed paths for read/write."""
    global RESTRICT_PATHS
    if len(RESTRICT_PATHS) == 0:
        return True
    for folder in RESTRICT_PATHS:
        if os.path.abspath(path).startswith(os.path.abspath(folder) + '/'):
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

def symlink(filefrom, fileto, fromlocal=False, tolocal=False):
    """Make a symlink. *local variables indicate whether the paths must be
    explicitly allowed or not."""
    if fromlocal and not isInRestrict(filefrom):
        raise Exception("Loading file `%s` not allowed." % filefrom)
    if tolocal and not isInRestrict(fileto):
        raise Exception("Loading file `%s` not allowed." % fileto)
    os.symlink(filefrom, fileto)


def filecopy(filefrom, fileto, fromlocal=False, tolocal=False, makedirs=False):
    """Copy a file. *local variables indicate whether the paths must be
    explicitly allowed or not."""
    if fromlocal and not isInRestrict(filefrom):
        raise Exception("Loading file `%s` not allowed." % filefrom)
    if tolocal and not isInRestrict(fileto):
        raise Exception("Loading file `%s` not allowed." % fileto)
    if makedirs:
        try:
            os.makedirs(os.path.dirname(fileto))
        except:
            pass
    shutil.copy2(filefrom, fileto)


def dircopy(originDir, destDir, overwrite=True):
    """Copy all files and subdirectories from a folder to another one.
    If a destination file exists, it will be overwritten if overwrite is True,
    else the original file will not be copied."""
    for (dirpath, dirnames, filenames) in os.walk(originDir):
        dirRelPath = os.path.relpath(originDir, dirpath)
        try:
            os.makedirs(os.path.join(destDir, dirRelPath))
        except:
            pass
        for f in filenames:
            filecopy(os.path.join(originDir, dirRelPath, f), os.path.join(destDir, dirRelPath, f))


def isExecError(executionReport, checkContinue=True):
    """Returns whether an execution returned an error according to its exit
    code. checkContinue means that we also return False if the continueOnError
    flag is True."""
    return (executionReport['exitCode'] != 0 and
            not (checkContinue and executionReport.get('continueOnError', False)))


def capture(path, name='', truncateSize=-1):
    """Capture a file contents for inclusion into the output JSON as a
    captureReport object."""
    if not isInRestrict(path):
        raise Exception("Opening file `%s` for capture is not allowed.")
    report = {'name': name,
              'sizeKb': os.path.getsize(path) / 1024}
    fd = open(path, 'r')
    if truncateSize <= 0:
        tSize = CFG_MAX_GETFILE
    else:
        tSize = min(truncateSize, CFG_MAX_GETFILE)
    report['data'] = fd.read(tSize)
    report['wasTruncated'] = (len(fd.read(1)) > 0)
    fd.close()
    return report


def evaluation(evaluationParams):
    """Full evaluation process."""

    global RESTRICT_PATHS

    logging.info("Initializing evaluation")

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
        raise Exception("Task path `%s` invalid (folder not found)." % evaluationParams['taskPath'])

    # *** Variables handling
    varData = {'ROOT_PATH': evaluationParams['rootPath'],
               'TASK_PATH': evaluationParams['taskPath']}

    # Load path restriction if present
    if evaluationParams.has_key('restrictToPaths'):
        RESTRICT_PATHS = evaluationParams['restrictToPaths']
    else:
        RESTRICT_PATHS = []

    # Load a "preprocessing" JSON node or file
    defParamsPath = os.path.join(evaluationParams['taskPath'], 'defaultParams.json')
    if os.path.isfile(defParamsPath):
        try:
            varData.update(json.load(open(defParamsPath, 'r')))
        except:
            raise Exception("defaultParams.json in `%s` is invalid." % evaluationParams['taskPath'])

    if evaluationParams.has_key('extraParams'):
        exp = evaluationParams.pop('extraParams')
        if type(exp) is str and isInRestrict(exp):
            varData.update(json.load(open(exp, 'r')))
        else:
            varData.update(exp)


    # Check for evaluation elements
    for elem in ['generators', 'generations', 'extraTests', 'sanitizer',
                 'checker', 'solutions', 'executions']:
        if not evaluationParams.has_key(elem):
            # Get the default one defined by the task
            elemKey = 'defaultEvaluation%s%s' % (elem[0].upper(), elem[1:])
            if varData.has_key(elemKey):
                evaluationParams[elem] = '@%s' % elemKey
            else:
                raise Exception("Input JSON doesn't have key '%s', and no default for this key was defined by the task." % elem)

    # Path where the evaluation will take place
    if evaluationParams.has_key('outputPath'):
        if '../' in evaluationParams['outputPath']:
            raise Exception("Output path `%s` invalid." % evaluationParams['outputPath'])
        baseWorkingDir = os.path.join(CFG_BUILDSDIR, evaluationParams['outputPath'])
    else:
        # Make a new build folder in the build pool
        buildPoolTries = 0
        baseWorkingDir = '/'
        while os.path.isdir(baseWorkingDir):
            baseWorkingDir = os.path.join(CFG_BUILDSDIR, '_build%d/' % random.randint(10000*buildPoolTries, 10000*(buildPoolTries+1)))
            buildPoolTries += 1
    os.mkdir(baseWorkingDir)

    report = {}

    varData['BUILD_PATH'] = baseWorkingDir
    report['buildPath'] = baseWorkingDir
    if len(RESTRICT_PATHS) > 0:
        RESTRICT_PATHS.append(baseWorkingDir)

    evaluationParams = preprocessJson(evaluationParams, varData)

    cache = CacheDatabase()

    # We validate the input JSON format
    if validate is not None:
        try:
            validate(evaluationParams, json.load(open(CFG_INPUTSCHEMA, 'r')))
        except Exception as err:
            raise Exception("Validation failed for input JSON, error message: %s" % str(err))
    else:
        logging.warning("Unable to import jsonschema library, continuing without input/output JSON validation.")


    os.mkdir(baseWorkingDir + "libs/")
    os.mkdir(baseWorkingDir + "tests/")

    errorSoFar = False

    logging.info("Evaluation taking place in dir `%s`" % baseWorkingDir)

    # *** Generators
    os.mkdir(baseWorkingDir + "generators/")
    report['generators'] = []
    generators = {}
    for gen in evaluationParams['generators']:
        logging.info("Compiling generator ID `%s`" % gen['id'])
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
        logging.info("Generation ID `%s`" % gen['id'])
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
                outputFiles=['*.in', '*.out', '*.h', '*.o', '*.java', '*.ml', '*.mli', '*.pas', '*.py'])
            errorSoFar = errorSoFar or isExecError(genReport['generatorExecution'])
            if gen.has_key('idOutputGenerator'):
                # We also have an output generator
                genReport['outputGeneratorExecution'] = outputGenerator.execute(genDir, outputFiles=['*.out'])
                errorSoFar = errorSoFar or isExecError(genReport['outputGeneratorExecution'])
            report['generations'].append(genReport)

            # We copy the generated test files
            for f in globOfGlobs(genDir, ['*.in', '*.out']):
                filecopy(f, baseWorkingDir + 'tests/')
            # We copy the generated lib files
            for f in globOfGlobs(genDir, ['*.h', '*.o', '*.java', '*.ml', '*.mli', '*.pas', '*.py']):
                filecopy(f, baseWorkingDir + 'libs/')

    # We add extra tests
    if evaluationParams.has_key('extraTests'):
        logging.info("Adding extraTests")
        for et in evaluationParams['extraTests']:
            filepath = os.path.join(baseWorkingDir, "tests", et['name'])
            if et.has_key('path') and et['path'] != '': # Get file by path
                if os.path.isfile(et['path']):
                    symlink(et['path'], filepath, fromlocal=True)
                else:
                    raise Exception("File not found: %s" % et['path'])
            elif et.has_key('content'): # Content given in descr
                open(filepath, 'w').write(et['content'].encode('utf-8'))

    logging.info("Preparing sanitizer and checker")

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
        logging.info("Compiling solution ID `%s`" % sol['id'])
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
        logging.info("Starting evaluation execution")
        if test['idSolution'] in solutionsWithErrors:
            # This solution didn't compile
            continue
        solution = solutions[test['idSolution']]

        mainTestReport = {
            'id': test['id'],
            'name': test['idSolution'],
            'testsReports': []}
        testDir = "%sexecutions/%s.%s/" % (baseWorkingDir, test['idSolution'], test['id'])
        os.mkdir(testDir)

        # Prepare solution execution
        solution.prepareExecution(test['runExecution'])

        # List of delayed checks
        if CFG_MULTICHECK:
            multiCheckList = []

        # Files to test as input
        testFiles = globOfGlobs(os.path.join(baseWorkingDir, 'tests/'), test['filterTests'])
        for tf in testFiles:
            logging.debug("Test file `%s`" % tf)
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

            if CFG_MULTICHECK:
                # We delay the checking to later
                multiCheckList.append((len(mainTestReport['testsReports']), baseTfName))
            else:
                subTestReport['checker'] = checker.execute(testDir,
                    args="%s.solout %s.in %s.out" % tuple([baseTfName]*3),
                    stdinFile=testDir + baseTfName + '.out',
                    stdoutFile=testDir + baseTfName + '.ok',
                    otherInputs=[testDir + baseTfName + '.in', testDir + baseTfName + '.solout'])
            mainTestReport['testsReports'].append(subTestReport)

        # Execute delayed checks
        if CFG_MULTICHECK:
            multiCheckReports = multiChecker(testDir, multiCheckList, checker, evaluationParams['checker']['runExecution'])
            for (i, checkReport) in multiCheckReports:
                mainTestReport['testsReports'][i]['checker'] = checkReport

        report['executions'].append(mainTestReport)

    # We validate the output JSON format
    if validate is not None:
        try:
            validate(report, json.load(open(CFG_OUTPUTSCHEMA, 'r')))
        except Exception as err:
            raise Exception("Validation failed for output JSON, error message: %s" % str(err))
    else:
        logging.info("Unable to import jsonschema library, output JSON was not validated.")

    return report


if __name__ == '__main__':
    # Read command line options
    argParser = argparse.ArgumentParser(description="This simple tool manages every step of grading a contest task, from the generation of test data to the grading of a solution output.")

    argParser.add_argument('-d', '--debug', help='Show debug information (implies -v)', action='store_true')
    argParser.add_argument('-L', '--logfile', help='Write logs into file LOGFILE', action='store', metavar='LOGFILE')
    argParser.add_argument('-v', '--verbose', help='Be more verbose', action='store_true')

    args = argParser.parse_args()

    # Some options imply others
    args.verbose = args.verbose or args.debug

    # Add configuration from config.py
    if CFG_LOGFILE and not args.logfile:
        args.logfile = CFG_LOGFILE

    # Set logging options
    logLevel = getattr(logging, CFG_LOGLEVEL, logging.CRITICAL)
    if args.debug: logLevel = min(logLevel, logging.DEBUG)
    if args.verbose: logLevel = min(logLevel, logging.INFO)

    logConfig = {'level': logLevel,
        'format': '%(asctime)s - taskgrader - %(levelname)s - %(message)s'}
    if args.logfile: logConfig['filename'] = args.logfile
    logging.basicConfig(**logConfig)

    if args.logfile and args.verbose:
        # Also show messages on stderr
        logStderr = logging.StreamHandler()
        logStderr.setFormatter(logging.Formatter('%(asctime)s - taskgrader - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(logStderr)

    # Read input JSON
    try:
        inJson = json.load(sys.stdin)
    except Exception as err:
        raise Exception("Input data is not valid JSON: %s" % err)

    # Evaluation
    try:
        json.dump(evaluation(inJson), sys.stdout)
    except TemporaryException as err:
        # We use a different exit codes depending on the exception
        logging.critical("TemporaryException raised")
        logging.critical(traceback.format_exc())
        traceback.print_exc()
        sys.exit(2)
    except UnsupportedLanguage as err:
        logging.critical("UnsupportedLanguage raised: %s" % err.msg)
        logging.critical(traceback.format_exc())
        traceback.print_exc()
        sys.exit(3)
    except:
        logging.critical("Exception raised")
        logging.critical(traceback.format_exc())
        traceback.print_exc()
        sys.exit(1)

    # Auto-clean builds and cache every hour
    if CFG_CLEAN_AUTO:
        try:
            lastClean = float(open(CFG_CLEAN_TIMESTAMP, 'r').read())
        except:
            lastClean = 0
        if time.time() - lastClean > 3600:
            logging.info("Executing auto-clean script.")
            open(CFG_CLEAN_TIMESTAMP, 'w').write(str(time.time()))
            cleanProc = subprocess.Popen([CFG_CLEAN_SCRIPT])
            cleanProc.wait()
        else:
            logging.info("Auto-clean done recently, not executing script.")
