#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Sanitizer

# Example valid input:
# 3
# 0 1 1
# 1 0 2
# 0 0 1
# (size, then size*size grid)

from sys import exit, stdin
from sol_reference import solveGomoku

if __name__ == '__main__':
    # Read grid size
    try:
        size = int(stdin.readline().strip())
    except:
        print "Line 1 must be size (an int)."
        exit(1)

    # Read grid
    curLine = 0
    wasEmpty = False
    grid = []
    for l in stdin:
        # Stop on empty line
        if l.strip():
            curLine += 1
        elif wasEmpty:
            # Check the rest of the file is empty
            print "Unexpected extra data at the end of the test case."
            exit(1)
        else:
            wasEmpty = True
            continue

        # Try to read line
        try:
            gridLine = map(int, l.split())
        except:
            print "Couldn't parse grid line #%d: `%s`." % (curLine, l.strip())
            exit(1)

        # Check size and contents
        if len(gridLine) != size:
            print "Wrong size for grid line #%d: %d instead of %d." % (curLine, len(gridLine), size)
            exit(1)
        for (i, p) in enumerate(gridLine):
            if p not in [0, 1, 2]:
                print "Wrong player for line #%d, pawn #%d: %d (must be 0, 1 or 2)." % (curLine, i+1, p)
                exit(1)

        grid.append(gridLine)

    # Check number of lines
    if curLine != size:
        print "Wrong number of grid lines: got %d lines, expected %d." % (curLine, size)
        exit(1)

    # All tests passed, we check for multiple solutions
    allAligns = solveGomoku(size, grid, findAll=True)
    if len(allAligns) > 1:
        print "Found multiple sets of 5 aligned pawns:"
        for (row, col, player) in allAligns:
            print "winning set from (%d, %d) for player %d" % (row+1, col+1, player)
        exit(1)

    exit(0)
