#!/usr/bin/env python2.7
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


# This is an example checker program, but every part of the checking process
# can be configured.
# The output must be the grade from 0 to 100 on the first line, then any
# message on the next lines.
# The exit code must only be non-zero if the checker encountered some problem
# during checking, else it must be zero for both good and bad answers.


import sys

def computeAnswer(inputData):
    """Compute the answer to the task, from the input data."""
    # Do some calculations on the inputData
    answer = str(int(inputData) * 2)

    # EDIT ME (remove this line once done)

    return answer


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print "Error: invalid number of arguments."
        sys.exit(1) # Exit code of 1 means a checker error

    # Read the solution answer (test.solout)
    solAnswer = open(sys.argv[1], 'r').read().strip()
    # Read the test case data (test.in)
    inputData = open(sys.argv[2], 'r').read().strip()

    # A checker will normally compute the answer by itself, or use a reference
    # solution for that; next line will use the above function "computeAnswer".
    expected = computeAnswer(inputData)

    # But if the checker needs to read the expected answer (test.out),
    # use this line:
    #expected = open(sys.argv[3], 'r').read().strip()

    # At the end, the checker outputs the grade from 0 to 100 (first line),
    # then optionnally gives some more information on next lines.
    if solAnswer == expected:
        # Good answer
        print "100"
    else:
        # Bad answer
        print "0"
        print "Solution answered `%s`, expected answer was `%s`." % (solAnswer, expected)
    sys.exit(0)
