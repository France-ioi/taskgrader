#!/usr/bin/env python2

# This solution tests the cache system.
# It outputs a different number each time; if cache is effectively used, the
# test should get the same output from two executions of the taskgrader with
# the same task.

import time

time.sleep(1)
print int(1000*time.time())
