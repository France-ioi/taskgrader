#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Checking program: checks the output of the solution is the expected output

import json, sys, turtle
from PIL import Image
from StringIO import StringIO

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


def ratioImage():
    """Compute the ratio of black pixels in the output image."""
    # Open image
    # The image is stored by the runner in 'turtle_png.b64', and is
    # base64-encoded. We need to first decode it before loading in PIL.
    imgData = open('turtle_png.b64', 'r').read().decode('base64')
    imgData = StringIO(imgData)
    img = Image.open(imgData)

    # Read pixel data
    pixels = img.getdata()
    nbBlack = 0
    nbTotal = 0
    for r, g, b in pixels:
        nbTotal += 1
        # Test if black
        if r < 5 and g < 5 and b < 5:
            nbBlack += 1

    return int(nbBlack*100/nbTotal)


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
    logOk = checkTurtleLog(solLog, target)

    # Check the image
    imgRatio = ratioImage()
    imgOk = (imgRatio >= 45 and imgRatio <= 55)
    if logOk and imgOk:
        # Criterias were satisfied
        print "100"
    elif logOk or imgOk:
        # Only one criteria was satisfied
        print "50"
        if logOk:
            # Target position criteria was satisfied, not image
            print "Target position was reached, but image was only %d%% black." % imgRatio
        else:
            # Target image black ratio was satisfied, not log
            print "Target image black ratio was reached, but target position was not."
    else:
        # Criteria was never satisfied
        print "0"
