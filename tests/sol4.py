#!/usr/bin/env python2

import random, sys, time

start_time = time.time()
while time.time()-start_time < 5:
    x = random.randint(2, 1024) * random.randint(1, 1024)

print int(sys.stdin.read())*2
