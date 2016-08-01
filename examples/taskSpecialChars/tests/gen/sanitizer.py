#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import sys
caseData = sys.stdin.read().strip().decode('utf-8')

exitCode = 0

for (pos, c) in enumerate(caseData):
    if c not in [u'à', u'é']:
        print "Character `%s` at pos %d not allowed." % (c, pos+1)
        exitCode = 1

sys.exit(exitCode)
