#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# Installation script for the taskgrader.

import argparse, os, shutil, subprocess, sys

SELFDIR = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))


### Utility functions

def is_exe(path):
    """Checks a path is an executable."""
    return os.path.isfile(path) and os.access(path, os.X_OK)

def which(name):
    """Searches for a program in PATH."""
    if type(name) is list:
        return len(filter(None, map(which, name))) == len(name)

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

def missing(nameList):
    """Returns missing programs from nameList."""
    return filter(lambda x: which(x) is False, nameList)



### Installers

class Installer(object):
    """Installs something."""

    dependencies = []
    intro = ''
    name = ''

    def __init__(self, errors, warnings):
        self.errors = errors
        self.warnings = warnings

        if not self.intro:
            self.intro = 'Installing %s...' % self.name

    def execute(self, program, args=[], msg=None, output=False):
        if output:
            optStdout = None
            optStderr = None
        else:
            optStdout = subprocess.PIPE
            optStderr = subprocess.STDOUT
        progPath = which(program)
        progProc = subprocess.Popen([progPath] + args, stdout=optStdout, stderr=optStderr)
        progOut, _ = progProc.communicate()
        if progProc.returncode > 0:
            if msg:
                self.printErr(msg)
            else:
                self.printErr("Command `%s` failed." % ' '.join([progPath] + args))
            if not output:
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
        depsMissing = missing(self.dependencies)
        if depsMissing:
            self._depsError(depsMissing)
            return False
        return True

    def _run(self):
        return True

    def run(self):
        if not self.checkDependencies():
            return False

        return self._run()

    def needRoot(self):
        return False

    def _runRoot(self):
        return True

    def runRoot(self):
        if not self.checkDependencies():
            return False

        return self._runRoot()


class BaseDependencies(Installer):
    dependencies = ['python', 'python2.7']
    intro = "Checking for required binaries..."
    name = 'Base dependencies'

    def _depsError(self, depsMissing):
        self.printErr("Dependencies %s are missing, please install them before continuing." % ', '.join(depsMissing))


class AllDependencies(Installer):
    dependencies = ['fpc', 'g++', 'gcc', 'gcj', 'git', 'nodejs', 'ocamlopt', 'php5', 'python3']
    intro = "Checking for recommended binaries..."
    name = 'Recommended dependencies'

    def _depsError(self, depsMissing):
        self.printWarn("Dependencies %s are missing, some features will not work properly." % ', '.join(depsMissing))


class GitSubmodule(Installer):
    dependencies = ['git']
    submodule = ''

    def _run(self):
        return self.execute('git', ['submodule', 'update', '--init', self.submodule], 'Git submodule update failed for %s.' % self.submodule)


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

        if not self.execute('make', ['-C', 'isolate', 'isolate'], 'Isolate compilation failed.'):
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
        return (self.execute('chown', ['root:root', 'isolate-bin']) and self.execute('chmod', ['4755', 'isolate-bin']))


class Jvs2Java(GitSubmodule):
    dependencies = ['git', 'gcj']
    submodule = 'Jvs2Java'
    name = 'Jvs2Java'

    def _run(self):
        if not super(Jvs2Java, self)._run():
            return False

        return self.execute('gcj',  ['--encoding=utf8', '--main=Jvs2Java', '-o', 'jvs2java', 'Jvs2Java/Jvs2Java.java'], 'Jvs2Java compilation failed.')


class BoxRights(Installer):
    dependencies = ['gcc']
    name = 'box-rights'

    def _run(self):
        if not super(BoxRights, self)._run():
            return False

        return self.execute('gcc', ['-O3', '-o', 'box-rights', 'box-rights.c'], 'box-rights compilation failed.')

    def needRoot(self):
        return True

    def _runRoot(self):
        return (self.execute('chown', ['root:root', 'box-rights']) and self.execute('chmod', ['4755', 'box-rights']))


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

        return (not error)


class DataDirectories(Installer):
    dependencies = []
    name = 'Data directories'

    def _run(self):
        return self.execute('./cache_reset.py', [], 'Data directories initialization failed.')


class FetchV8(Installer):
    dependencies = ['git', 'gcc', 'make']
    name = 'V8 Javascript engine'

    def _run(self):
        print("/!\ V8 installation is very long, and will take about 2GB of disk space.\n")
        try:
            os.mkdir('v8-install')
        except:
            pass
        if not self.execute('git', ['clone', 'https://chromium.googlesource.com/chromium/tools/depot_tools.git', 'v8-install/depot_tools'], msg='Chromium depot_tools clone failed.', output=True):
            return False
        oldPath = os.environ['PATH']
        os.environ['PATH'] = "%s:%s" % (os.path.join(SELFDIR, 'v8-install/depot_tools/'), os.environ['PATH'])

        os.chdir(os.path.join(SELFDIR, 'v8-install'))
        if not self.execute('fetch', ['v8'], msg='V8 clone failed.', output=True):
            os.chdir(SELFDIR)
            os.environ['PATH'] = oldPath
            return False

        os.chdir(os.path.join(SELFDIR, 'v8-install/v8'))
        if not self.execute('make', ['native'], msg='V8 compilation failed.', output=True):
            os.chdir(SELFDIR)
            os.environ['PATH'] = oldPath
            return False

        d8Path = os.path.join(SELFDIR, 'v8-install/v8/out/ia32.release/d8')
        if not is_exec(d8Path):
            d8Path = os.path.join(SELFDIR, 'v8-install/v8/out/x64.release/d8')

        os.chdir(SELFDIR)
        os.environ['PATH'] = oldPath

        if is_exec(d8Path):
            os.symlink(d8Path, os.path.join(SELFDIR, 'v8-install/d8'))
            return True
        else:
            self.printErr("Couldn't find d8 binary.")
            return False



### Main

if __name__ == '__main__':
    print("""/!\ This installer is still experimental. If it doesn't work, please
execute old-install.sh.
""")

    validInstallers = ['AllDependencies', 'JsonSchema', 'Isolate', 'Jvs2Java', 'BoxRights', 'ConfigFiles', 'DataDirectories', 'FetchV8']

    # Read command line options
    argParser = argparse.ArgumentParser(description="Install taskgrader and some of its dependencies.")

    argParser.add_argument('-r', '--root', help="Install bits which need root permissions", action='store_true')
    argParser.add_argument('-i', '--install', help="Install a specific component", action='append', choices=validInstallers)

    args = argParser.parse_args()

    errors = []
    warnings = []

    os.chdir(SELFDIR)

    if not args.root:
        try:
            args.root = (os.geteuid() == 0)
        except:
            pass

    if not BaseDependencies(errors, warnings).run():
        print("Aborting.")
        sys.exit(1)

    installers = [AllDependencies, JsonSchema, Isolate, Jvs2Java, BoxRights, ConfigFiles, DataDirectories]
    rootInstallers = []

    if args.install:
        installers = []
        for cls in args.install:
            installers.append(eval(cls))
        print("Installing only %s" % (', '.join(args.install)))

    for instClass in installers:
        inst = instClass(errors, warnings)
        if not args.root:
            print("*** %s" % inst.intro)
            res = inst.run()
        if inst.needRoot():
            rootInstallers.append(inst)

    rootOk = True
    if args.root:
        for inst in rootInstallers:
            print("*** %s (root mode)" % inst.intro)
            inst.runRoot()

        if errors or warnings:
            print("%d errors, %d warnings on root installation" % (len(errors), len(warnings)))
            if errors:
                print("Errors:")
                print("\n".join(errors))
            if warnings:
                print("Warnings:")
                print("\n".join(errors))
            sys.exit(1)
        else:
            sys.exit(0)

    elif rootInstallers:
        rootOk = False
        if which('sudo'):
            print("Launching 'sudo' to get root privileges...")
            procRet = subprocess.call([which('sudo'), './install.py', '--root'])
            if procRet != 0:
                errors.append("root installation failed")
                print("sudo ./install.py --root failed")
            else:
                rootOk = True

        if not rootOk:
            print("""
Please execute this script again as root or with the --root command-line switch
to execute root-only operations.""")

    print("\nInstallation summary: %d errors, %d warnings." % (len(errors), len(warnings)))
    if errors:
        print("Installation failed. Please check the errors:")
        print("\n".join(errors))
        if warnings:
            print("and warnings:")
            print("\n".join(warnings))
    elif warnings:
        print("Installation complete. Some warnings occured, please check them:")
        print("\n".join(warnings))
    else:
        print("Installation completed without errors. You can now use the taskgrader!")
