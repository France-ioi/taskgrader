#!/usr/bin/env python3

# Copyright (c) 2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This tool imports solutions and test cases from a zip file.

import os, subprocess, sys, zipfile

SELFDIR = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
CFG_TESTSELECT = os.path.join(SELFDIR, 'testSelect.py')

CFG_LANGEXTS = {
    '.c': 'c',
    '.cpp': 'cpp',
    '.py': 'python',
    '.py2': 'python2',
    '.py3': 'python3',
    '.ml': 'ocaml',
    '.java': 'java',
    '.js': 'nodejs',
    '.jvs': 'javascool',
    '.pas': 'pascal',
    '.sh': 'shell',
    '': 'sh'
    }

def unzip(zipFile, testsPath, solsPath):
    """Unzip a zip export into testsPath and solsPath."""
    newTests = []
    newSols = []

    # Explore list of files in the zip archive
    for name in zipFile.namelist():
        folder, filename = os.path.split(name)
        if folder:
            # Rename a/b/c.ext to b-c.ext
            newFilename = '%s-%s' % (os.path.split(folder)[1], filename)
        else:
            newFilename = filename
        r, ext = os.path.splitext(newFilename)
        # Check type of file from extension
        if ext == '.in':
            newTestPath = os.path.join(testsPath, newFilename)
            newTests.append(newTestPath)
            newFile = open(newTestPath, 'wb')
        elif ext in ['.c', '.cpp', '.py', '.py2', '.py3', '.ml', '.pas', '.js', '.java', '.jvs', '.sh']:
            newSolPath = os.path.join(solsPath, newFilename)
            newSols.append(newSolPath)
            newFile = open(newSolPath, 'wb')
        else:
            # Not a test nor solution
            continue
        # Extract file directly to target path
        newFile.write(zipFile.open(name).read())
        newFile.close()

    return (newTests, newSols)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Please specify a zip file to import.")
        sys.exit(1)

    if not (os.path.isfile('taskSettings.json') or os.path.isfile('testSelect.json') or os.path.isdir('tests')):
        print("Current folder isn't a task. Aborting.")
        sys.exit(1)

    try:
        zipFile = zipfile.ZipFile(sys.argv[1])
    except:
        print("Unable to open zip file '%s'." % sys.argv[1])
        sys.exit(1)

    # Paths to store the tests and solutions in
    testsPath = 'tests/importedtests/'
    solsPath = 'tests/importedsols/'
    try:
        os.makedirs(testsPath)
    except:
        pass
    try:
        os.makedirs(solsPath)
    except:
        pass

    print("*** Extracting files from zip...")
    newTests, newSols = unzip(zipFile, testsPath, solsPath)
    print("Extracted %d test cases, %d solutions." % (len(newTests), len(newSols)))

    # Import into testSelect
    print("\n*** Importing into testSelect...")
    if len(newTests) > 0:
        subprocess.check_call([CFG_TESTSELECT, 'addtest'] + newTests)
    if len(newSols) > 0:
        # Fetch language for each solution
        # We optimize the number of calls to testSelect by grouping solutions for each language
        solLangs = {}
        for sol in newSols:
            r, ext = os.path.splitext(sol)
            try:
                lang = CFG_LANGEXTS[ext]
            except:
                print("""
Warning: Couldn't detect language for `%s`.
Please import manually with the command:
  testSelect.py addsol -l [LANG] %s""" % (sol, sol))
                continue
            if lang in solLangs:
                solLangs[lang].append(sol)
            else:
                solLangs[lang] = [sol]

        # Launch testSelect for each language/solutions
        for lang in solLangs.keys():
            subprocess.check_call([CFG_TESTSELECT, 'addsol', '-l', lang] + solLangs[lang])

    print("\n*** Computing new coverage information...")
    subprocess.check_call([CFG_TESTSELECT, 'compute'])

    print("\n*** Selecting tests...")
    subprocess.check_call([CFG_TESTSELECT, 'compute'])

    print("""
All done!
Use `testSelect.py serve` to see current solutions/tests coverage,
and `testSelect.py export` to export selected tests into the task.""")
