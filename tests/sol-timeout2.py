#!/usr/bin/env python2.7

# This program tests the wall time limit, waiting for 6 seconds before finishing.

import sys, time

time.sleep(6)

print int(sys.stdin.read())*2
