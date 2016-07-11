#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Read input
a = int(input())
b = int(input())

# Get min and max
m = max(a, b)
t = min(a, b)

# Addition loop
r = 0
while t > 0:
    r += m
    t -= 1

# Print result
print(r)
