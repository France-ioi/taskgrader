#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import json, sys, traceback
import turtle
from functools import partial


class LoggedTurtle(object):
    """Class emulating Turtle behavior while logging all commands.
    It won't actually display anything, it will only execute movement commands
    through a TNavigator.
    The class' log variable will contain the log for all LoggedTurtles."""

    log = []
    next_id = 0

    def _log(self, items):
        """Add to log."""
        self.__class__.log.append(items)

    def __init__(self, *args, **kwargs):
        # Turtle ID
        self.tid = self.__class__.next_id
        self.__class__.next_id += 1

        # Navigator which will handle all movements
        self.navigator = turtle.TNavigator()
        self.navigator.speed(0)

        # Log initialization
        self._log((self.tid, 'turtle', '__init__', args, kwargs))

    def logNavigator(self, *args, **kwargs):
        # Log a movement command and execute it
        funcName = kwargs.pop('funcName')
        self._log((self.tid, 'nav', funcName, args, kwargs))
        return getattr(self.navigator, funcName)(*args, **kwargs)

    def logTurtle(self, *args, **kwargs):
        # Log a non-movement command
        funcName = kwargs.pop('funcName')
        self._log((self.tid, 'turtle', funcName, args, kwargs))

    def __getattr__(self, attr):
        # Handle calls to this class

        # Check if it's a movement command
        if hasattr(self.navigator, attr):
            subAttr = getattr(self.navigator, attr)
            if hasattr(subAttr, '__call__'):
                return partial(self.logNavigator, funcName=attr)
            else:
                return subAttr

        # Check if it's another Turtle command
        elif hasattr(turtle.Turtle, attr):
            subAttr = getattr(turtle.Turtle, attr)
            if hasattr(subAttr, '__call__'):
                return partial(self.logTurtle, funcName=attr)
            else:
                return subAttr

        # Not a Turtle command at all
        else:
            raise AttributeError 


def changeTurtle(scriptPath):
    """Modify a script to use the LoggedTurtle."""
    newScriptLines = []
    for l in open(scriptPath, 'r'):
        # Remove turtle from imports
        if l[:6] == 'import':
            imported = map(lambda x: x.strip(), l[7:].strip().split(','))
            if 'turtle' in imported:
                imported.remove('turtle')
            if len(imported) > 0:
                newScriptLines.append("import %s\n" % ', '.join(imported))

        # Modify Turtle instances to LoggedTurtle instances
        if 'Turtle' in l:
            newl = l.replace('turtle.Turtle(', 'LoggedTurtle(')
            newl = newl.replace('Turtle(', 'LoggedTurtle(')
            newl = newl.replace('LoggedLoggedTurtle', 'LoggedTurtle') # safety
            newScriptLines.append(newl)
        else:
            newScriptLines.append(l)

    open(scriptPath, 'w').writelines(newScriptLines)


# Modify the solution
changeTurtle("solution.py")

# Execute the solution
try:
    execfile("solution.py")
except:
    # Remove the runner from the traceback
    excInfo = sys.exc_info()
    traceback.print_exception(excInfo[0], excInfo[1], excInfo[2].tb_next)
    sys.exit(1)

# Output as JSON
print(json.dumps(LoggedTurtle.log))
