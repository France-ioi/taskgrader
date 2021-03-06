#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

### genStdTaskJson.py configuration
# Default solution compilation and execution parameters
CFG_EXECPARAMS = {
    'timeLimitMs': 60000,
    'memoryLimitKb': 128*1024,
    'useCache': True,
    'stdoutTruncateKb': -1,
    'stderrTruncateKb': -1,
    'getFiles': []
    }

# Languages supported, file extension -> language
CFG_LANGEXTS = {
    '.adb': 'ada',
    '.c': 'c',
    '.cpp': 'cpp',
    '.py': 'python',
    '.py2': 'python2',
    '.py3': 'python3',
    '.ml': 'ocaml',
    '.java': 'java',
    '.jvs': 'javascool',
    '.pas': 'pascal',
    '.sh': 'shell',
    '': 'sh'
    }

### We raise an exception if we don't have all configuration variables
for var in ['CFG_EXECPARAMS', 'CFG_LANGEXTS']:
    if var not in globals():
        raise Exception("Configuration variable %s missing. Please edit config.py." % var)
