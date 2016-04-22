#!/bin/bash

# Generation script
# A generator builds needed files for the task, such as libraries or test files.
#
# Files generated should follow the same tree conventions as the `files' folder,
# that is
#   lib/[language]/file.ext for libraries
#   *.in and *.out for test cases
#
# The libraries and test cases will automatically be added as available
# dependencies and test cases for solutions.
#
# An usual generator should just generate files upon execution; for advanced
# options please check the taskgrader documentation.

# If you change the path of the generator, execute
#   taskstarter.py add generator [path_to_new_generator]
# to update task settings.
# Note that the generator must be a shell script.

# *** EXAMPLES: (delete these lines)
# (replace mytestgenerator, refsolution and mylibrarygenerator with your own scripts)

# Write a test case
echo "5 2 3" > gen-test01.in
# Generate another test case with some script
./mytestgenerator.sh > gen-test02.in

# Compute the expected answers by using the reference solution
gcc -o refsolution refsolution.c
./refsolution < gen-test01.in > gen-test01.out
./refsolution < gen-test02.in > gen-test02.out

# Generate a library
./mylibrarygenerator.sh lib/c/mylib.h
# *** End of examples

# EDIT ME (remove this line once this script is written)

exit 0
