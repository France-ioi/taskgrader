#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# This checker checks whether the solution gave the minimum of the three
# numbers.

import sys

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print "Error: invalid number of arguments."
        sys.exit(1) # Exit code of 1 means a checker error

    # Read the test case data
    # (Note that no error can happen here as the test case format was checked
    # by the sanitizer.)
    inputData = open(sys.argv[2], 'r').read().split()
    expected = min(map(int, inputData))

    # Read the solution answer
    solAnswer = open(sys.argv[1], 'r').read()
    try:
        solAnswerInt = int(solAnswer)
    except:
        # Not an integer, we give a grade of 0
        print "0"
        print "Solution answered `%s` which isn't an int." % solAnswer.strip()
        sys.exit(0)

    if solAnswerInt == expected:
        # Good answer
        print "100"
    else:
        # Bad answer
        print "0"
        print "Solution answered `%d`, expected answer was `%d`." % (solAnswerInt, expected)
