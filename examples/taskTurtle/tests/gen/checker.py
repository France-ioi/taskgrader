#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Checking program: checks the output of the solution is the expected output

import json, sys, turtle

def checkTurtleLog(log, target):
    """Check the turtle log is what we expected."""
    # List with all the turtles
    turtles = []
    for entry in log:
        # tid: ID number for the turtle (to allow multiple turtles)
        # comp: component, either 'nav' for the navigator, 'turtle' for other
        #   functions
        # funcName: name of turtle's function called
        # largs, lkwargs: args and kwargs of the call
        tid, comp, funcName, largs, lkwargs = entry

        # Create turtles when needed
        if tid >= len(turtles):
            if tid != len(turtles):
                # The ID should increase by one each time, not more
                raise Exception("Turtle ID error")
            if funcName == '__init__':
                # We only care about the position
                # A TNavigator is like a turtle but without the drawing part
                t = turtle.TNavigator()
                t.speed(0)
                turtles.append(t)
            else:
                raise Exception("Turtle used before initialization.")
            # Turtle was created, we go to the next log entry
            continue

        # EXAMPLE: check at least one turtle went through the position 'target'

        # Replay only movements
        if comp == 'nav':
            t = turtles[tid]
            getattr(t, funcName)(*largs, **lkwargs)
        else:
            # Nothing changed, go to next log entry
            continue

        # CRITERIA
        # Check our criteria on the current turtle (the others didn't change)
        # We can have a criteria over multiple turtles by referencing them
        # through the 'turtles' list
        # Here the criteria is to go to the target position (from the input
        # test case)
        if t.position() == target:
            return True

    # The log is finished and the criteria was never satisfied
    return False


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print "Error: invalid number of arguments."
        sys.exit(1) # Exit code of 1 means a checker error

    # Read the solution turtle log
    try:
        solLog = json.load(open(sys.argv[1], 'r'))
    except:
        raise Exception("Solution output is not valid JSON.")
        sys.exit(1) # It's a task error

    # Read the test case data (test.in)
    target = tuple(map(int, open(sys.argv[2], 'r').read().split()))

    # Check the log
    if checkTurtleLog(solLog, target):
        # Criteria was satisfied
        print "100"
    else:
        # Criteria was never satisfied
        print "0"
