#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

import os, sqlite3

### taskgrader.py configuration
# Base directory for work files, will contain the builds and cache
CFG_BASEDIR = ''
# Base directory for binaries, must contain the different binaries needed
CFG_BINDIR = ''

CFG_BUILDSDIR = os.path.join(CFG_BASEDIR, 'builds/')
CFG_CACHEDIR = os.path.join(CFG_BASEDIR, 'cache/')
CFG_DATABASEPATH = os.path.join(CFG_CACHEDIR, 'taskgrader-cache.sqlite')

CFG_ISOLATEBIN = os.path.join(CFG_BINDIR, 'isolate')
CFG_RIGHTSBIN = os.path.join(CFG_BINDIR, 'box-rights')
CFG_JAVASCOOLBIN = os.path.join(CFG_BINDIR, 'FranceIOIJvs2Java')

CFG_JSONSCHEMA = os.path.join(CFG_BINDIR, 'jsonschema')
CFG_INPUTSCHEMA = os.path.join(CFG_BINDIR, 'schema_input.json')
CFG_OUTPUTSCHEMA = os.path.join(CFG_BINDIR, 'schema_output.json')

# Time and memory parameter transformations for some languages
# For memory, we only transform the limit
# Example: CFG_TRANSFORM_MEM={'c': lambda x: 4096+x}
CFG_TRANSFORM_MEM  = {}
# For time, each dict entry is a tuple (transform_func, untransform_func)
# Example: CFG_TRANSFORM_TIME={'c': (lambda x: x * 0.9, lambda x: x / 0.9)}
CFG_TRANSFORM_TIME = {}


### grade.py configuration
# Path to the taskgrader
CFG_TASKGRADER = os.path.join(CFG_BINDIR, 'taskgrader.py')

# Default solution compilation and execution parameters
CFG_EXECPARAMS = {'timeLimitMs': 60000,
                  'memoryLimitKb': 128*1024,
                  'useCache': True,
                  'stdoutTruncateKb': -1,
                  'stderrTruncateKb': -1,
                  'getFiles': []}

# Languages supported, file extension -> language
CFG_LANGEXTS = {'.c': 'c',
                '.cpp': 'cpp',
                '.py': 'py',
                '.ml': 'ocaml',
                '.java': 'java',
                '.jvs': 'javascool',
                '.pas': 'pascal',
                '.sh': 'sh',
                '': 'sh'}


### We raise an exception if we don't have all configuration variables
for var in ['CFG_BASEDIR', 'CFG_BUILDSDIR', 'CFG_CACHEDIR', 'CFG_DATABASEPATH',
            'CFG_BINDIR', 'CFG_ISOLATEBIN', 'CFG_RIGHTSBIN', 'CFG_JAVASCOOLBIN',
            'CFG_JSONSCHEMA', 'CFG_TRANSFORM_MEM', 'CFG_TRANSFORM_TIME',
            'CFG_TASKGRADER', 'CFG_EXECPARAMS', 'CFG_LANGEXTS']:
    if var not in globals():
        raise Exception("Configuration variable %s missing. Please edit config.py." % var)

for var in ['CFG_BASEDIR', 'CFG_BINDIR']:
    if var == '':
        raise Exception("Configuration variable %s empty. Please edit config.py." % var)

### Initialization
# Make directories if they don't exist
try:
    os.mkdir(CFG_BUILDSDIR)
except:
    pass
try:
    os.mkdir(CFG_CACHEDIR)
except:
    pass

# Initialize the database if needed
CFG_DATABASE = sqlite3.connect(CFG_DATABASEPATH)
try:
    CFG_DATABASE.execute("""CREATE TABLE cache
            (id INTEGER PRIMARY KEY,
             filesid TEXT,
             hashlist TEXT)""")
except:
    pass
CFG_DATABASE.row_factory = sqlite3.Row

