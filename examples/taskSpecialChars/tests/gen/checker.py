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

import sys

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print "Error: invalid number of arguments."
        sys.exit(1) # Exit code of 1 means a checker error

    # Read the solution answer (test.solout)
    solAnswer = open(sys.argv[1], 'r').read().strip()
    # Read the test case data (test.in)
    inputData = open(sys.argv[2], 'r').read().strip().decode('utf-8')

    try:
        solAnswerSplit = solAnswer.split()
        if len(solAnswerSplit) != 4 or (solAnswerSplit[1] != 'à' or solAnswerSplit[3] != 'é'):
            raise Exception() # Same checker message
        solAnswera = int(solAnswerSplit[0])
        solAnswere = int(solAnswerSplit[2])
    except:
        print "0"
        print "Solution answered `%s` instead of a count '3 à 5 é'." % solAnswer
        sys.exit(0)

    # Compute the answer
    (counta, counte) = (0, 0)
    for c in inputData:
        if c == u'à':
            counta += 1
        elif c == u'é':
            counte += 1
        else:
            # Shouldn't happen as the sanitizer checked the test case
            print "Error: character `%s` invalid." % c
            sys.exit(1) # Checker error

    # At the end, the checker outputs the grade from 0 to 100 (first line),
    # then optionnally gives some more information on next lines.
    if (solAnswera, solAnswere) == (counta, counte):
        # Good answer
        print "100"
        print "You found the right number of `à`s and `é`s!"
    else:
        # Bad answer
        print "0"
        print "Solution answered (%d, %d), expected answer was (%d, %d)." % (solAnswera, solAnswere, counta, counte)
    sys.exit(0)
