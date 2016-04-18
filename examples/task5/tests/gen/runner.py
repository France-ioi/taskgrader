#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# This is the runner of this task: it reads the input, and then executes the
# function 'min3nombres' of the solution

import sys

# Import the function min3nombres from the solution
from solution import min3nombres

if __name__ == '__main__':
    # Read the input
    # The sanitizer ensures the input will always be three numbers
    nb1, nb2, nb3 = sys.stdin.read().split()
    # Execute the solution
    print min3nombres(int(nb1), int(nb2), int(nb3))
