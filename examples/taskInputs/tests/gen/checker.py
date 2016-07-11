#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Checking program: checks the output of the solution is the expected output


import sys

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print "Error: invalid number of arguments."
        sys.exit(1) # Exit code of 1 means a checker error

    # Read the test input (input)
    inputInt = int(open('input', 'r').read().strip())

    # Read the solution answer (output)
    try:
        solAnswer = open('output', 'r').read().strip()
    except:
        # Solution didn't write the 'output' file
        print "0"
        print "No 'output' file was written by the solution."
        sys.exit(0)

    # Convert answer to int
    try:
        solAnswerInt = int(solAnswer)
    except:
        # Answer is not an int
        print "0"
        print "Solution didn't answer an integer."
        sys.exit(0)

    # At the end, the checker outputs the grade from 0 to 100 (first line),
    # then optionnally gives some more information on next lines.
    if solAnswerInt == 2 * inputInt:
        # Good answer
        print "100"
    else:
        # Bad answer
        print "0"
        print "Solution answered `%d`, expected answer was `%s`." % (solAnswerInt, 2 * inputInt)
    sys.exit(0)
