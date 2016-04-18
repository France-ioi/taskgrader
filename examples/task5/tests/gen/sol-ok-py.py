#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Example solution for this task
# Defines the function min3nombres which is then used by the runner

def min3nombres(a, b, c):
    # Return the minimum of 3 numbers
    # (as would the Python function 'min' do!)
    if a < b:
        if a < c:
            return a
        else:
            return c
    else:
        if b < c:
            return b
        else:
            return c
