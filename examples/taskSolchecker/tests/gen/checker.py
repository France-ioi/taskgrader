#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Checking program: checks the output of the solution is the expected output

# This checking program also checks the solution source file. In this example,
# the criteria is the number of characters of the source code, excluding lines
# which are empty or just comments.

import re, string, sys

# Number of characters of a "good" solution
GOOD_CHARCOUNT = 60
# Number of points removed by character above the good char count
EXTRA_CHAR_PENALTY = 1
# Minimum grade for a correct solution (but with too many characters)
MINIMUM_GOOD_GRADE = 50

# List of patterns (regular expressions) of lines to ignore
LINE_IGNORE_PATTERNS = [
    '^\s*$', # Empty line
    '^\s*#', # Comment starting with '#'
    '^\s*//' # Comment starting with '//'
    ]

def checkSolution():
    """Check the number of characters of the solution."""
    # The taskSettings add the solution as a file in the execution folder, with
    # the filename 'solution'
    solFile = open('solution', 'r')

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
    # Read the expected answer (test.out)
    expectedInt = int(open(sys.argv[3], 'r').read().strip())

    # Check the solution answer is an int
    try:
        solAnswerInt = int(solAnswer)
    except:
        # Answer was not an int, invalid result anyway
        print "0"
        print "Solution answered `%s` which isn't an int." % solAnswer
        sys.exit(0)

    if solAnswerInt == expectedInt:
        # Good answer
        charCount = checkSolution()
        if charCount <= GOOD_CHARCOUNT:
            # Solution has the right number of characters
            print "100"
        else:
            # Solution has too many characters, compute partial grade
            grade = max(100-EXTRA_CHAR_PENALTY*(charCount-GOOD_CHARCOUNT), MINIMUM_GOOD_GRADE)
            print grade
            print "Solution answer good, but solution has %d characters, which is more than the" % charCount
            print "maximum number of characters %d." % GOOD_CHARCOUNT
    else:
        # Bad answer
        print "0"
        print "Solution answered `%s`, expected answer was `%s`." % (solAnswer, expectedInt)
    sys.exit(0)
