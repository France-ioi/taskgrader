#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This cron file deletes old builds and cache entries. It deletes on time and
# space criterias.

import os, shutil, sqlite3, time

# Local imports
from config import *

def getFolderSize(path):
    """Get the size of a folder recursively."""
    itemList = os.listdir(path)
    totalSize = 0
    for item in itemList:
        itemPath = os.path.join(path, item)
        if os.path.isdir(itemPath):
            totalSize += getFolderSize(itemPath)
        elif os.path.isfile(itemPath):
            totalSize += os.path.getsize(itemPath)
    return totalSize


def getBuildTime(path):
    """Get the modification time for a build folder."""
    return os.path.getmtime(path)

def getCacheTime(path):
    """Get the last access time (if available) for a cache folder."""
    try:
        atimeFile = open(os.path.join(path, 'cache.ok'), 'r')
        return float(atimeFile.read())
    except:
        return 0

def pruneDir(path, olderThan, maxSize, timeFunction):
    """Prune a folder, deleting all folders older than a specific time, and
    then deleting oldest folders until the size criteria is satisfied."""
    delList = []
    infoList = []
    totalSize = 0

    # Select folders older than olderThan for deletion
    for folder in os.listdir(path):
        folderPath = os.path.join(path, folder)
        if os.path.isdir(folderPath):
            folderTime = timeFunction(folderPath)
            if folderTime < olderThan:
                delList.append(folder)
            else:
                folderSize = getFolderSize(folderPath)
                totalSize += folderSize
                infoList.append((folder, folderTime, folderSize))

    # Select oldest folders for deletion until total size is under maxSize
    infoList.sort(key=lambda t: t[1])
    while totalSize > maxSize:
        (folder, folderTime, folderSize) = infoList.pop()
        delList.append(folder)
        totalSize -= folderSize

    # Delete the folders
    for folder in delList:
        shutil.rmtree(os.path.join(path, folder))

    # Return the remaining folders
    return infoList


if __name__ == '__main__':
    # Delete builds
    infoBuilds = pruneDir(CFG_BUILDSDIR, time.time()-CFG_BUILDS_MAXTIME, CFG_BUILDS_MAXSIZE, getBuildTime)

    # Delete cache entries
    infoCache = pruneDir(CFG_CACHEDIR, time.time()-CFG_CACHE_MAXTIME, CFG_CACHE_MAXSIZE, getCacheTime)

    # Clean cache database
    database = sqlite3.connect(CFG_CACHEDBPATH)
    database.row_factory = sqlite3.Row
    foldersCache = map(lambda t: t[0], infoCache)
    dbCur = database.cursor()
    dbCur.execute("DELETE FROM cache WHERE id NOT IN (%s)" % ','.join(foldersCache))
    dbCur.execute("VACUUM")
    database.commit()
