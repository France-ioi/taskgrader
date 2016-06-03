#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Checking program: checks the output of the solution is the expected output

# This checking program also checks the solution source file. In this example,
# the criteria is the number of characters of the source code, excluding lines
# which are empty or just comments.

import re, string, sys

def checkSolution():
    """Check the number of characters of the solution."""
    # Compile regular expression patterns
    lineIgnorePatterns = map(re.compile, LINE_IGNORE_PATTERNS)
    # Check the number of characters
    charCount = 0
    for line in solFile:
        if len(filter(None, map(lambda x: x.match(line), lineIgnorePatterns))) == 0:
            # No match was found, the line is a regular line
            # We add the number of non-whitespace characters to the total count
            cleanedLine = line.translate(None, string.whitespace)
            charCount += len(cleanedLine)

    return charCount


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print "Error: invalid number of arguments."
        sys.exit(1) # Exit code of 1 means a checker error

    # Read the solution answer (test.solout)
    solAnswer = open(sys.argv[1], 'r').read().strip()
    # Read the input
    # (not needed in this checker)
    #inputData = open(sys.argv[2], 'r').read().strip()
    # Read the expected answer (test.out)
    expectedInt = int(open(sys.argv[3], 'r').read().strip())

    # Open the solution file
    # The taskSettings add the solution as a file in the execution folder, with
    # the filename 'solution'
    solFile = open('solution', 'r')

    # Open the compilation stdout and stderr
    compOut = open('compilationStdout', 'r')
    compErr = open('compilationStderr', 'r')

    if not solAnswer:
        # Solution didn't answer anything, check the compilation message
        # Modify this part to personalize the behavior of the checker

        compErrMsg = compErr.read()
        if not compErrMsg:
            # No compiler message, the solution compiled but didn't answer
            # anything
            print "0"
            print "Solution didn't answer anything."
        else:
            # Example : just give a grade of 0 and print the compiler message
            print "0"
            print compErrMsg

    else:
        # Check the solution answer is an int
        try:
            solAnswerInt = int(solAnswer)
        except:
            # Answer was not an int, invalid result
            print "0"
            print "Solution answered `%s` which isn't an int." % solAnswer
            sys.exit(0)

        if solAnswerInt == expectedInt:
            # Good answer
            print "100"
        else:
            print "0"
            print "Solution answered %d, expected answer %d." % (solAnswerInt, expectedInt)
    sys.exit(0)
