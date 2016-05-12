#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Example bad solution for this task
# Defines the function min3nombres which is then used by the runner

def min3nombres(a, b, c):
    # Bad solution: we return the max instead of the min
    if a < b:
        if b < c:
            return c
        else:
            return b
    else:
        if a < c:
            return c
        else:
            return a
