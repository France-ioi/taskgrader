#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Example solution for this task

import turtle

targetX, targetY = map(int, raw_input().split())

# First turtle to validate the position criteria
t = Turtle()
t.forward(targetX)
t.left(90)
t.forward(targetY)

# Second turtle to fill half of the screen
t2 = Turtle()
t2.begin_fill()
t2.forward(400)
t2.left(90)
t2.forward(300)
t2.left(90)
t2.forward(800)
t2.left(90)
t2.forward(300)
t2.left(90)
t2.forward(400)
t2.end_fill()
