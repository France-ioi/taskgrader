#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Example solution for this task

import turtle

targetX, targetY = map(int, raw_input().split())

t = Turtle()
t.forward(targetX)
t.left(90)
t.forward(targetY)

# We can even do whatever afterwards it will still validate the criteria
t2 = Turtle()
t2.left(50)
t2.forward(100)

t.begin_fill()
t.circle(80)
t.end_fill()
