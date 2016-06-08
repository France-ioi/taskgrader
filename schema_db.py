#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# schema.py: definition for the cache database
# This little script initializes the cache database.

import os, sqlite3

from config_default import CFG_CACHEDBPATH
try:
    from config import CFG_CACHEDBPATH
except:
    pass

def schemaDb():
    db = sqlite3.connect(CFG_CACHEDBPATH)
    db.execute("""CREATE TABLE IF NOT EXISTS cache
    (id INTEGER PRIMARY KEY,
     filesid TEXT,
     hashlist TEXT)""")

if __name__ == '__main__':
    schemaDb()
