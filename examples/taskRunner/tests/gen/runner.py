#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# This is the runner of this task: it reads the input, and then executes the
# function 'min3nombres' of the solution

import sys, traceback

# Import the function min3nombres from the solution
try:
    from solution import min3nombres
except:
    # Remove the runner from the traceback
    excInfo = sys.exc_info()
    traceback.print_exception(excInfo[0], excInfo[1], excInfo[2].tb_next)
    sys.exit(1)

if __name__ == '__main__':
    # Read the input
    # The sanitizer ensures the input will always be three numbers
    nb1, nb2, nb3 = sys.stdin.read().split()
    # Execute the solution
    print min3nombres(int(nb1), int(nb2), int(nb3))
