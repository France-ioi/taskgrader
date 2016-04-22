#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# The sanitizer ensures each test case is valid.
# It is given the test case input on its standard input, and must indicate an
# exit code of 0 if the test case is valid, or 1 if it is invalid to signal the
# taskgrader to not use this test case.

# This is an example sanitizer program, edit it for your task needs.

import sys

if __name__ == '__main__':
    # Read the input
    inputData = sys.stdin.read().strip()

    # Do stuff with the input
    # EDIT ME (remove this line once done)


    # EXAMPLE: check the test case is 3 numbers

    # Get all elements in the test case
    elements = inputData.split()

    # Check the number of elements
    if len(elements) == 3:
        # Check each element is a number, else tell which element is not
        for i, s in enumerate(elements):
            try:
                n = int(s)
            except:
                # Couldn't decode an element as int, we output the error
                print "Test case invalid: element #%d, `%s`, is not a number." % (i, s)
                # Exit code 1 to indicate the test case is invalid
                sys.exit(1)

        # Tests passed, we exit with 0 to indicate the test case is valid
        sys.exit(0)
    else:
        # Length invalid
        print "Test case invalid: expected 3 elements, got %d instead." % len(elements)
        # Exit code 1 to indicate the test case is invalid
        sys.exit(1)
