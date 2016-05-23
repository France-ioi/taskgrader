#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Imports
import matplotlib
import matplotlib.pyplot as plt

# Read input
plotlist = map(int, raw_input().split())

# Make a figure
fig = plt.figure()
ax = fig.add_subplot(111)
ax.plot(plotlist)

# Return the figure
returnFig(fig)
