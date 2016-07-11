#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Checking program: checks the output of the solution is the expected output
# Takes three arguments on command-line:
#   ./checker test.solout test.in test.out
# where
#   test.solout is the solution output
#   test.in is the test input given to the solution
#   test.out is the expected output (if given by the task, else an empty file)
# If you change the path of the checker, execute
#   taskstarter.py add checker [path_to_new_checker]
# to update task settings.

import sys

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print "Error: invalid number of arguments."
        sys.exit(1) # Exit code of 1 means a checker error

    # Read the solution answer (test.solout)
    solAnswer = open(sys.argv[1], 'r').read().strip()
    # Read the test case data (test.in)
    inputData = map(int, open(sys.argv[2], 'r').read().strip().split())
    # Read the expected answer
    expected = open(sys.argv[3], 'r').read().strip()


    # Fetch lines from the solution output
    solAnswerLines = solAnswer.split('\n')
    # Statistics line
    solTotals = solAnswerLines[-1].split()

    # Check statistics line
    if len(solTotals) == 0 or solTotals[0] != 'totals:':
        print "0"
        print "Solution didn't execute properly."
        sys.exit(1)

    # Number of additions
    nbAdds = int(solTotals[1])
    # Number of substractions
    nbSubs = int(solTotals[2])
    # Number of multiplications
    nbMuls = int(solTotals[3])
    # Number of divisions
    nbDivs = int(solTotals[4])


    # Actual solution answer (with the runner's statistics line stripped
    solAnswerClean = '\n'.join(solAnswerLines[:-1]).strip()

    # Check the answer
    if solAnswerClean == expected:
        # Answer is right, check the number of operations
        if nbAdds > min(inputData) or nbSubs > min(inputData):
            # Too many additions or substractions
            print "80"
            print "Answer is right, but you can do it with less operations."
        else:
            # Good answer
            print "100"
    else:
        # Mauvaise reponse
        print "0"
        print "Solution answered `%s`, expected `%s`." % (solAnswerClean, expected)
    sys.exit(0)
