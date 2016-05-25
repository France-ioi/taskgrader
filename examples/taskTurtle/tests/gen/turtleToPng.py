#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import json, os, subprocess, sys, time, turtle, warnings
from PIL import Image
from StringIO import StringIO

def replayTurtleLog(log, speed=6):
    """Replay a turtle log."""
    turtles = []
    for entry in log:
        # tid: ID for the turtle (to allow multiple turtles)
        # comp: component, either 'nav' for the navigator, 'turtle' for other
        #   functions
        # funcName: name of turtle's function called
        # largs, lkwargs: args and kwargs of the call
        tid, comp, funcName, largs, lkwargs = entry
        if tid >= len(turtles):
            if tid != len(turtles):
                raise Exception("Turtle ID error")
            if funcName == '__init__':
                t = turtle.Turtle(*largs, **lkwargs)
                # Speed up the turtle if needed
                t.speed(speed)
                turtles.append(t)
            else:
                raise Exception("Turtle used before initialization.")
        else:
            t = turtles[tid]
            getattr(t, funcName)(*largs, **lkwargs)


def getTurtlePng(log):
    """Get the base64-encoded data of the resulting image of turtle
    movements."""
    # Put the window size to 600x450 (for some reason turtle reduces the
    # numbers by 25%)
    turtle.setup(width=800, height=600)

    # Start turtle replay
    replayTurtleLog(log, speed=0)

    # Output as postscript
    psStr = StringIO(turtle.Screen().getcanvas().postscript())

    # Remove PIL warnings
    warnings.filterwarnings('ignore')

    # Read with PIL and output as PNG
    img = Image.open(psStr)
    imgStr = StringIO()
    img.save(imgStr, format='PNG')

    # Return base64-encoded PNG
    return imgStr.getvalue().encode('base64')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Error: invalid number of arguments."
        sys.exit(1)

    # Read the turtle log
    try:
        solLog = json.load(open(sys.argv[1], 'r'))
    except:
        # The runner is supposed to give a correct log, it's a task error
        print "Invalid turtle log."
        sys.exit(1)

    # Replay log
    print getTurtlePng(solLog)
