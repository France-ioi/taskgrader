#!/bin/bash

# Generation script
# A generator builds needed files for the task, such as libraries or test files.
#
# Files generated should follow the same tree conventions as the `files' folder,
# that is
#   lib/[language]/file.ext for libraries
#   test.in and test.out for test cases
#
# The libraries and test cases will automatically be added as available
# dependencies and test cases for solutions.
#
# An usual generator will just generate files upon execution; for advanced
# options please check the taskgrader documentation.

# If you change the path of the generator, execute
#   taskstarter.py add generator [path_to_new_generator]
# to update task settings.
# Note that the generator must be a shell script.
