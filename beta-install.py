#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

import os, shutil, subprocess, sys

SELFDIR = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))

class DependencyManager(object):
    """Manages dependencies found."""

    def __init__(self):
        self.deps = {}

    def is_exe(self, path):
        return os.path.isfile(path) and os.access(path, os.X_OK)

    def _search(self, name):
        """Searches for a program in PATH."""
        fpath, basename = os.path.split(name)
        if fpath and self.is_exe(name):
            return name
        else:
            for spath in os.environ['PATH'].split(os.pathsep):
                spath = spath.strip('"')
                fullpath = os.path.join(spath, name)
                if self.is_exe(os.path.join(spath, name)):
                    return fullpath
        return False

    def has(self, name):
        """Searches for a program in PATH, using cache if possible.
        Can accept a list of names, will then return whether all programs in
        the list were found."""
        if type(name) is list:
            return len(filter(None, map(self.has, name))) == len(name)

        if name not in self.deps:
            self.deps[name] = self._search(name)
        return self.deps[name]

    def missing(self, nameList):
        """Returns missing programs from nameList."""
        return filter(lambda x: self.has(x) is False, nameList)


class Installer(object):
    """Installs something."""

    dependencies = []
    intro = ''
    name = ''

    def __init__(self, dm, errors, warnings):
        self.dm = dm
        self.errors = errors
        self.warnings = warnings

    def execute(self, dm, program, args, msg=None):
        progPath = dm.has(program)
        progProc = subprocess.Popen([progPath] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        progOut, _ = progProc.communicate()
        if progProc.returncode > 0:
            if msg:
                self.printErr(msg)
            else:
                self.printErr("Command `%s` failed." % ' '.join([progPath] + args))
            print("Command output:")
            print(progOut)
            return False
        return True

    def printErr(self, msg):
        self.errors.append(msg + "\n")
        print("[ERROR] %s" % msg)

    def printWarn(self, msg):
        self.warnings.append(msg + "\n")
        print("[Warning] %s" % msg)

    def _depsError(self, depsMissing):
        self.printWarn("Skipping %s because dependencies '%s' are missing." % (self.name, ', '.join(depsMissing)))

    def checkDependencies(self):
        depsMissing = dm.missing(self.dependencies)
        if depsMissing:
            self._depsError(depsMissing)
            return False
        return True

    def _run(self):
        return True

    def run(self):
        if self.intro:
            print(self.intro)
        else:
            print("*** Installing %s" % self.name)
        if not self.checkDependencies():
            return False

        return self._run()

    def needRoot(self):
        return False

    def _runRoot(self):
        return True

    def runRoot(self):
        if self.intro:
            print("%s (root operations)" % self.intro)
        else:
            print("*** Installing %s (root operations)" % self.name)
        if not self.checkDependencies():
            return False

        return self._runRoot()


class BaseDependencies(Installer):
    dependencies = ['python', 'python2.7']
    intro = "*** Checking for required binaries..."
    name = 'Base dependencies'

    def _depsError(self, depsMissing):
        self.printErr("Dependencies %s are missing, please install them before continuing." % ', '.join(depsMissing))


class AllDependencies(Installer):
    dependencies = ['fpc', 'g++', 'gcc', 'gcj', 'git', 'nodejs', 'ocamlopt', 'php5', 'python3']
    intro = "*** Checking for recommended binaries..."
    name = 'Recommended dependencies'

    def _depsError(self, depsMissing):
        self.printWarn("Dependencies %s are missing, some features will not work properly." % ', '.join(depsMissing))


class GitSubmodule(Installer):
    dependencies = ['git']
    submodule = ''

    def _run(self):
        return self.execute(dm, 'git', ['submodule', 'update', '--init', self.submodule], 'Git submodule update failed for %s.' % self.submodule)


class JsonSchema(GitSubmodule):
    submodule = 'jsonschema'
    name = 'JsonSchema'


class Isolate(GitSubmodule):
    dependencies = ['git', 'make', 'gcc']
    submodule = 'isolate'
    name = 'Isolate'

    def _run(self):
        if not super(Isolate, self)._run():
            return False

        if not self.execute(dm, 'make', ['-C', 'isolate', 'isolate'], 'Isolate compilation failed.'):
            return False

        try:
            shutil.copy2('isolate/isolate', 'isolate-bin')
        except:
            self.printErr("Failed copying compiled `isolate` binary to `isolate-bin`.")
            return False

        return True

    def needRoot(self):
        return True

    def _runRoot(self):
        return (self.execute(dm, 'chown', ['root:root', 'isolate-bin']) and self.execute(dm, 'chmod', ['4755', 'isolate-bin']))


class Jvs2Java(GitSubmodule):
    dependencies = ['git', 'gcj']
    submodule = 'Jvs2Java'
    name = 'Jvs2Java'

    def _run(self):
        if not super(Jvs2Java, self)._run():
            return False

        return self.execute(dm, 'gcj',  ['--encoding=utf8', '--main=Jvs2Java', '-o', 'jvs2java', 'Jvs2Java/Jvs2Java.java'], 'Jvs2Java compilation failed.')


class BoxRights(Installer):
    dependencies = ['gcc']
    name = 'box-rights'

    def _run(self):
        if not super(BoxRights, self)._run():
            return False

        return self.execute(dm, 'gcc', ['-O3', '-o', 'box-rights', 'box-rights.c'], 'box-rights compilation failed.')

    def needRoot(self):
        return True

    def _runRoot(self):
        return (self.execute(dm, 'chown', ['root:root', 'box-rights']) and self.execute(dm, 'chmod', ['4755', 'box-rights']))


class ConfigFiles(Installer):
    dependencies = []
    name = 'Config files'

    def _run(self):
        error = False
        for cfgFile in ['config', 'tools/genJson/config', 'tools/remoteGrader/remote_config', 'tools/stdGrade/config']:
            destPath = os.path.join(SELFDIR, "%s.py" % cfgFile)
            if not os.path.isfile(destPath):
                try:
                    shutil.copy2(os.path.join(SELFDIR, "%s_default.py" % cfgFile), destPath)
                except Exception as e:
                    error = True
                    self.printErr("Error while setting up config file `%s`:\n%s" % (destPath, str(e)))

        return error


class DataDirectories(Installer):
    dependencies = []
    name = 'Data directories'

    def _run(self):
        return self.execute(dm, './cache_reset.py',  [], 'Data directories initialization failed.')


if __name__ == '__main__':
    dm = DependencyManager()

    errors = []
    warnings = []

    os.chdir(SELFDIR)

    rootMode = False
    try:
        rootMode = (os.geteuid() == 0)
    except:
        pass

    if not BaseDependencies(dm, errors, warnings).run():
        print("Aborting.")
        sys.exit(1)

    installers = [AllDependencies, JsonSchema, Isolate, Jvs2Java, BoxRights, ConfigFiles, DataDirectories]
    rootInstallers = []

    for instClass in installers:
        inst = instClass(dm, errors, warnings)
        if not rootMode:
            inst.run()
        if inst.needRoot():
            rootInstallers.append(inst)

    if rootMode:
        for inst in rootInstallers:
            inst.runRoot()
