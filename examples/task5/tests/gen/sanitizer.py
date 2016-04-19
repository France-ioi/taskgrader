#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# This sanitizer ensures the input is a list of 3 numbers.
# Its exit code is 0 if the test case is valid, or 1 if it is invalid to signal
# the taskgrader to not use this test case.

import sys

if __name__ == '__main__':
    # Read the input
    inputData = sys.stdin.read()
    elements = inputData.split()
    if len(elements) == 3:
        # Check each element is a number, else tell which element is not
        for i, s in enumerate(elements):
            try:
                n = int(s)
            except:
                print "Test case invalid: element #%d, `%s`, is not a number." % (i, s)
                sys.exit(1)
        # Tests passed
        sys.exit(0)
    else:
        # Length invalid
        print "Test case invalid: expected 3 elements, got %d instead." % len(elements)
        sys.exit(1)
