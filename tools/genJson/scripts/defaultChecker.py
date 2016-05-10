#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Default checking program: checks the output of the solution is the given
# expected output (test.out).
# Takes three arguments on command-line:
#   ./defaultChecker.py test.solout test.in test.out
# where
#   test.solout is the solution output
#   test.in is the test input given to the solution (not used)
#   test.out is the expected output (if given by the task, else an empty file)

from json import dumps
from subprocess import Popen, PIPE
from sys import argv, exit

MAX_CHARS = 500

def diff(solPath, outPath):
    """Generate a diff report of two files."""

    # Execute diff
    diffProc = Popen(['/usr/bin/env', 'diff', '-bBu',
        solPath, outPath], stdout=PIPE)

    # Ignore first two lines
    do = diffProc.stdout
    do.readline()
    o = do.readline()

    # We cannot rely on returncode as diff can have closed its output without
    # being finished yet
    if not o:
        # The files are identical
        return (100, {})

    # The files aren't identical, analyze diff output

    # Import only because we need them
    from collections import OrderedDict
    from os.path import getsize
    from string import whitespace

    result = OrderedDict()

    # The chunk line is always the same for the two files, but if one file is
    # empty, diff will give a line number of 0
    chunkLine = max(int(do.readline().split()[2].split(',')[0]), 1)

    solLines = []
    expLines = []

    truncatedAfter = False

    # Read diff output
    curLine = chunkLine
    diffLine = None
    lastLine = do.readline()
    while lastLine:
        if lastLine[0] == ' ':
            solLines.append(lastLine[1:])
            expLines.append(lastLine[1:])
        elif lastLine[0] == '-':
            if diffLine is None:
                diffLine = curLine
            solLines.append(lastLine[1:])
        elif lastLine[0] == '+':
            if diffLine is None:
                diffLine = curLine
            expLines.append(lastLine[1:])

        curLine += 1
        lastLine = do.readline()

        # We read max 3 lines after the first difference
        if diffLine is not None and curLine-diffLine > 3:
            truncatedAfter = (lastLine != '')
            break

    # Find difference in the diff line
    relLine = diffLine-chunkLine
    solDLine = solLines[relLine]
    expDLine = expLines[relLine]
    solCur = 0
    expCur = 0
    while True:
        # We ignore consecutive whitespaces
        # It's a line so the character before the first one is a newline
        if solDLine[solCur] in whitespace:
            if solCur == len(solDLine)-1:
                break
            elif solCur == 0 or solDLine[solCur+1] in whitespace:
                solCur += 1
                continue
        if expDLine[expCur] in whitespace:
            if expCur == len(expDLine)-1:
                break
            elif expCur == 0 or expDLine[expCur+1] in whitespace:
                expCur += 1
                continue
        if solDLine[solCur] != expDLine[expCur]:
            break
        else:
            solCur += 1
            expCur += 1

    # Start building report
    result['msg'] = "Answer mismatch at line %d, character %d" % (diffLine, solCur+1)
    result['solutionOutputLength'] = getsize(solPath)
    result['diffRow'] = diffLine
    result['diffCol'] = solCur+1

    # Select lines to display
    if len(solDLine) > MAX_CHARS or len(expDLine) > MAX_CHARS:
        # We only display the differing line because it's already too long
        if solCur < MAX_CHARS/2:
            colStart = 0
            colEnd = MAX_CHARS
        elif len(solDLine) - solCur < MAX_CHARS/2:
            colStart = len(solDLine)-MAX_CHARS
            colEnd = max(len(solDLine), len(expDLine))
        else:
            colStart = solCur - MAX_CHARS/2
            colEnd = solCur + MAX_CHARS/2
        result['displayedSolutionOutput'] = solDLine[colStart:colEnd]
        result['displayedExpectedOutput'] = expDLine[colStart:colEnd]
        result['truncatedBefore'] = (diffLine > 1)
        result['truncatedAfter'] = True
        result['excerptRow'] = diffLine
        result['excerptCol'] = colStart+1

    else:
        # We add lines before and/or after as long as we stay within MAX_CHARS
        remChars = MAX_CHARS - max(len(solDLine), len(expDLine))
        dispStartLine = relLine
        dispEndLine = relLine
        while dispStartLine > 0:
            if len(solLines[dispStartLine-1]) > remChars:
                break
            else:
                remChars -= len(solLines[dispStartLine-1])
                dispStartLine -= 1
        while dispEndLine < min(len(solLines), len(expLines))-1:
            if len(solLines[dispEndLine+1]) > remChars:
                break
            else:
                remChars -= len(solLines[dispEndLine+1])
                dispEndLine += 1

        result['displayedSolutionOutput'] = ''.join(solLines[dispStartLine:dispEndLine+1])
        result['displayedExpectedOutput'] = ''.join(expLines[dispStartLine:dispEndLine+1])
        result['truncatedBefore'] = (dispStartLine + chunkLine > 1)
        result['truncatedAfter'] = truncatedAfter
        result['excerptRow'] = dispStartLine + chunkLine
        result['excerptCol'] = 1

    # Return a grade of 0 (answer mismatch) and the results info
    return (0, result)


if __name__ == '__main__':
    if len(argv) != 4:
        print "Error: invalid number of arguments."
        exit(1) # Exit code of 1 means a checker error

    grade, result = diff(argv[1], argv[3])
    print grade
    if grade != 100:
        print dumps(result)
