#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from StringIO import StringIO

SAVED_FIG = False

def changeImports(scriptPath):
    """Remove matplotlib imports from a script."""
    newScriptLines = []
    for l in open(scriptPath, 'r'):
        # Remove matplotlib from imports
        if l[:6] == 'import':
            imported = map(lambda x: x.strip(), l[7:].strip().split(','))
            if 'matplotlib' in imported:
                imported.remove('matplotlib')
            if len(imported) > 0:
                newScriptLines.append("import %s\n" % ', '.join(imported))
        else:
            newScriptLines.append(l)

    open(scriptPath, 'w').writelines(newScriptLines)


def returnFig(fig):
    """Save the result figure."""
    # We allow only for one figure to be returned.
    # Customize this function to allow for more figures.
    global SAVED_FIG
    if SAVED_FIG:
        raise Exception("A figure was already returned.")

    # Export figure
    imgStr = StringIO()
    fig.savefig(imgStr, format='png')

    # Save to output_png.b64
    output = open('output_png.b64', 'w')
    output.write(imgStr.getvalue().encode('base64'))
    SAVED_FIG = True


# Override getpass' getuser
# (matplotlib uses it, and getuser doesn't work inside isolate)
import getpass
def fakeuser(**kwargs):
    return "fakeuser"
getpass.getuser = fakeuser

import matplotlib
# Set up matplotlib to not display graphics
matplotlib.use('Agg')
# No user data
matplotlib.rcParams['datapath'] = '.'

# Execute the solution
changeImports("solution.py")
execfile("solution.py")

# Check a figure was saved
if SAVED_FIG:
    print "ok"
else:
    print "no figure returned"
