#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# This program is not meant to be time nor memory efficient.
# It is a reference program doing computations and using memory.

from __future__ import print_function

MAX_NUMBER = 20000

primes = []
for i in range(2, MAX_NUMBER):
    for j in range(2, i):
        if i % j == 0:
            primes.append(False)
            break
    else:
        primes.append(True)
        print("%d " % i, end='')
print("are primes.")
