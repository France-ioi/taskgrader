#!/bin/bash
RESULT=$((`cat $2`*2))
SOLOUTDATA=`cat $1`
if ! [ "$SOLOUTDATA" -eq "$RESULT" ] 2> /dev/null
then
  echo "0"
  exit 1
else
  echo "100"
  exit 0
fi
