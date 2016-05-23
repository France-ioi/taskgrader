#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# This checker checks whether the solution saved a figure.

import sys

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print "Error: invalid number of arguments."
        sys.exit(1) # Exit code of 1 means a checker error

    # Read the solution answer
    solAnswer = open(sys.argv[1], 'r').read().strip()
    # We only check whether the solution saved a figure.
    if solAnswer == "ok":
        print "100"
    else:
        print "0"
        print solAnswer
