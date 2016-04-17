#!/usr/bin/env python2.7

# This program tests CPU time limit, computing random stuff for 5 seconds.

import random, sys, time

start_time = time.time()
while time.time()-start_time < 5:
    # Do random stuff that can't be optimized.
    x = random.randint(2, 1024) * random.randint(1, 1024)

print int(sys.stdin.read())*2
