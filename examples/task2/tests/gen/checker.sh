#!/bin/bash

# This script is an example checker.
# It will be called by taskgrader in the following manner:
# checker.sh test.in test.solout test.out
# Thus $1 will contain the input number, $2 the output of the solution.
# The checker will give a grade of 100 if we got the expected result,
# a grade of 0 if the solution gave a wrong answer.

RESULT=$((`cat $2`*2))
SOLOUTDATA=`cat $1`
if ! [ "$SOLOUTDATA" -eq "$RESULT" ] 2> /dev/null
then
  echo "0"
  exit 0
else
  echo "100"
  exit 0
fi
