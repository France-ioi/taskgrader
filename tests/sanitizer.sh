#!/bin/bash
INPUTDATA=`cat`
if ! [ `echo "$INPUTDATA" |wc -l` -eq 1 ]
then
  echo "Input file must have only one line."
  exit 1
fi
if ! [ "$INPUTDATA" -eq "$INPUTDATA" ] 2> /dev/null
then
  echo "Input file is not a positive number."
  exit 1
fi
exit 0
