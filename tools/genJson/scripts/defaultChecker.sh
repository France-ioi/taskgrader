#!/bin/bash
if ! ( [ -f "$1" ] && [ -f "$2" ] && [ -f "$3" ] )
then
    echo "Usage: default_checker.sh test.solout test.in test.out"
    echo "with -test.solout the solution output"
    echo "     -test.in the reference input (unused)"
    echo "     -test.out the reference output"
    exit 1
fi
if diff -w $3 $1 > /dev/null
then
    echo "100"
else
    echo "0"
    diff -urw $3 $1
fi
exit 0
