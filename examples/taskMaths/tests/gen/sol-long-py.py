#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Read input
a = int(input())
b = int(input())

# Addition loop
# The mistake is to not check which one of a and b is the smallest to optimize
# the number of additions
r = 0
while a > 0:
    r += b
    a -= 1

# Print result
print(r)
