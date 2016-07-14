#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This little script resets the build folder and the cache database

import os, shutil

# Local imports
import schema_db
from config_default import CFG_BUILDSDIR, CFG_CACHEDIR
from config import CFG_BUILDSDIR, CFG_CACHEDIR

if __name__ == '__main__':
    # Delete the builds and the cache folder
    shutil.rmtree(CFG_BUILDSDIR, ignore_errors=True)
    shutil.rmtree(CFG_CACHEDIR, ignore_errors=True)
    # Recreate them
    os.makedirs(CFG_BUILDSDIR)
    os.makedirs(CFG_CACHEDIR)
    # Reinitialize the cache database
    schema_db.schemaDb()
