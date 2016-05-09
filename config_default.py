#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This is the configuration file for the taskgrader.
# Copy this file to 'config.py' and edit it to fit your needs.
# The default values from 'config_default.py' will be used if 'config.py'
# doesn't define them.

import os

##### START OF CONFIGURATION #####

### Paths ###

# Base directory for work files, will contain the builds and cache
# install.sh will change this folder to taskgrader's dir + 'files/'
CFG_BASEDIR = 'CHANGE_ME'
# Base directory for binaries, must contain the different binaries needed
# install.sh will change this folder to taskgrader's dir
CFG_BINDIR = 'CHANGE_ME'

# Internal folders for taskgrader operation
CFG_BUILDSDIR = os.path.join(CFG_BASEDIR, 'builds/')
CFG_CACHEDIR = os.path.join(CFG_BASEDIR, 'cache/')
CFG_CACHEDBPATH = os.path.join(CFG_CACHEDIR, 'taskgrader-cache.sqlite')

# Paths to binaries
CFG_ISOLATEBIN = os.path.join(CFG_BINDIR, 'isolate-bin')
CFG_RIGHTSBIN = os.path.join(CFG_BINDIR, 'box-rights')
CFG_JAVASCOOLBIN = os.path.join(CFG_BINDIR, 'jvs2java')

# jsonschema-related variables
CFG_JSONSCHEMA = os.path.join(CFG_BINDIR, 'jsonschema')
CFG_INPUTSCHEMA = os.path.join(CFG_BINDIR, 'schema_input.json')
CFG_OUTPUTSCHEMA = os.path.join(CFG_BINDIR, 'schema_output.json')


### Logging ###

# Log file (when not specified on command-line)
CFG_LOGFILE = None
# Log level, must be 'CRITICAL', 'ERROR', 'WARNING', 'INFO' or 'DEBUG'
CFG_LOGLEVEL = "WARNING"


### Execution ###

# Does the kernel support control groups?
CFG_CONTROLGROUPS = False

# Compile executables as static
# Possible values: 'auto', True, False
# 'auto' will be False on Mac OS X, True on other systems
CFG_STATIC = 'auto'

# Use only one isolated execution for all checker tests
# (improves performance as each isolate invocation is slow)
# If True, use a script inside isolate to do all checker invocations; it will
# not use the cache system. If False, use normal behavior of executing the
# checker in isolate for each test case.
CFG_MULTICHECK = True

# Timeout for accessing the cache
CFG_CACHE_TIMEOUT = 60


### Time and memory limits ###

# Maximum time and memory limits; if input JSON defines limits higher than
# that, the tasgrader will return an error
CFG_MAX_TIMELIMIT = 60000       # in milliseconds
CFG_MAX_MEMORYLIMIT = 1024*1024 # in kilobytes
CFG_MAX_GETFILE = 1024*1024     # in bytes

# Time and memory parameter transformations for some languages
# For memory, we only transform the limit
# Example: CFG_TRANSFORM_MEM={'c': lambda x: 4096+x}
CFG_TRANSFORM_MEM  = {}
# For time, each dict entry is a tuple (transform_func, untransform_func)
# Example: CFG_TRANSFORM_TIME={'c': (lambda x: x * 0.9, lambda x: x / 0.9)}
CFG_TRANSFORM_TIME = {}
# If no transformation is given for a language, we use the default
CFG_TRANSFORM_MEM_DEFAULT  = (lambda x: x)
CFG_TRANSFORM_TIME_DEFAULT = (lambda x: x, lambda x: x)


### Miscellaneous ###

# Execute clean_cache at the end of the taskgrader (every hour)
# Disable this if you already execute it (in graderserver for instance)
CFG_CLEAN_AUTO = True
# Cleaning script path
CFG_CLEAN_SCRIPT = os.path.join(CFG_BINDIR, 'clean_cache.py')

# clean_cache.py variables
# Max age (since creation) in seconds and total size in bytes for builds
CFG_BUILDS_MAXTIME = 7200         # Keep builds for 2 hours
CFG_BUILDS_MAXSIZE = 50*1024*1024 # Keep less than 50 MB of builds

# Max age (since last access) in seconds and total size for cache
CFG_CACHE_MAXTIME = 14*24*60*60   # Keep old cache for two weeks
CFG_CACHE_MAXSIZE = 250*1024*1024 # Keep less than 250 MB of cache


##### END OF CONFIGURATION #####
