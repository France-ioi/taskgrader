#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, traceback

# Configuration: allow or disallow each operation
ALLOW_OPERATION = {
    'add': True,
    'sub': True,
    'mul': False,
    'div': False
    }
TOTALS = {
    'add': 0,
    'sub': 0,
    'mul': 0,
    'div': 0
    }

class Number(int):
    """Class behaving like an integer, keeping track of operations done and
    raising an exception is the operation is disallowed by the task."""

    def __init__(self, value):
        self.value = value

    def __int__(self):
        return self.value

    def __add__(self, val):
        if not ALLOW_OPERATION['add']:
            raise Exception("Addition is forbidden in this task!")

        # Record the operation
        global TOTALS
        TOTALS['add'] += 1

        # Return a Number
        if type(val) is Number:
            return Number(self.value + val.value)
        else:
            return Number(self.value + val)

    # Reverse addition is the same
    __radd__ = __add__


    def __sub__(self, val):
        if not ALLOW_OPERATION['sub']:
            raise Exception("Substraction is forbidden in this task!")

        # Record the operation
        global TOTALS
        TOTALS['sub'] += 1

        # Return a Number
        if type(val) is Number:
            return Number(self.value - val.value)
        else:
            return Number(self.value - val)

    def __rsub__(self, val):
        if not ALLOW_OPERATION['sub']:
            raise Exception("Substraction is forbidden in this task!")

        # Record the operation
        global TOTALS
        TOTALS['sub'] += 1

        # Return a Number
        if type(val) is Number:
            return Number(val.value - self.value)
        else:
            return Number(val - self.value)


    def __mul__(self, val):
        if not ALLOW_OPERATION['mul']:
            raise Exception("Multiplication is forbidden in this task!")

        # Record the operation
        global TOTALS
        TOTALS['mul'] += 1

        # Return a Number
        if type(val) is Number:
            return Number(self.value * val.value)
        else:
            return Number(self.value * val)

    __rmul__ = __mul__

    def __div__(self, val):
        if not ALLOW_OPERATION['div']:
            raise Exception("Division is forbidden in this task!")

        # Record the operation
        global TOTALS
        TOTALS['div'] += 1

        # Return a Number
        if type(val) is Number:
            return Number(self.value / val.value)
        else:
            return Number(self.value / val)

    def __rdiv__(self, val):
        if not ALLOW_OPERATION['div']:
            raise Exception("Division is forbidden in this task!")

        # Record the operation
        global TOTALS
        TOTALS['div'] += 1

        # Return a Number
        if type(val) is Number:
            return Number(val.value / self.value)
        else:
            return Number(val / self.value)


# Replace the 'int' function by a custom function returning a Number
def int(val):
    return Number(__builtins__.int(val))

# Execute the solution
try:
    with open("solution.py") as f:
        code = compile(f.read(), "solution.py", 'exec')
        exec(code)
except:
    # Remove the runner from the traceback
    excInfo = sys.exc_info()
    traceback.print_exception(excInfo[0], excInfo[1], excInfo[2].tb_next)
    sys.exit(1)

# Display totals, will be read by the checker afterwards
print("") # Ensure there's a newline before
print("totals: %d %d %d %d" % (TOTALS['add'], TOTALS['sub'], TOTALS['mul'], TOTALS['div']))
