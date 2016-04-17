#!/usr/bin/env python2.7

# This solution tries to use a lot of memory to test the memory limits.

import sys

t = 1
t = [t]*1024
t = [t]*1024
t = [t]*1024
t = [t]*1024
print int(sys.stdin.read())*2
