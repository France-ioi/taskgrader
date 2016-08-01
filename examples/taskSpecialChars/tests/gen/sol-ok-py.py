#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import sys
caseData = sys.stdin.read().strip().decode('utf-8')

(counta, counte) = (0, 0)

for c in caseData:
    if c == u'à':
        counta += 1
    elif c == u'é':
        counte += 1

print "%d à %d é" % (counta, counte)
