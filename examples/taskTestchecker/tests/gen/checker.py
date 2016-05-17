#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Checking program: checks the output of the solution is the expected output
# Takes three arguments on command-line:
#   ./checker test.solout test.in test.out
# where
#   test.solout is the solution output
#   test.in is the test input given to the solution
#   test.out is the expected output (if given by the task, else an empty file)

import sys
from sol_reference import solveGomoku

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print "Error: invalid number of arguments."
        sys.exit(1) # Exit code of 1 means a checker error

    # Read the solution answer (test.solout)
    solAnswer = open(sys.argv[1], 'r').read().strip()
    # Read the test case data (test.in)
    inputFile = open(sys.argv[2], 'r')

    # Read input
    size = int(inputFile.readline().strip())
    grid = [list(map(int, inputFile.readline().split())) for i in range(size)]

    # Solve the task
    expected = solveGomoku(size, grid)

    # At the end, the checker outputs the grade from 0 to 100 (first line),
    # then optionnally gives some more information on next lines.
    try:
        solAnswerInt = int(solAnswer)
    except:
        # Answer wasn't an int
        print "0"
        print "Solution answered `%s` which is not an int." % solAnswer
        sys.exit(0)
    if solAnswerInt == expected:
        # Good answer
        print "100"
    else:
        # Bad answer
        print "0"
        print "Solution answered `%d`, expected answer was `%d`." % (solAnswerInt, expected)
    sys.exit(0)
