#!/bin/bash
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
if [ -n "$1" ]
then
  JSON="`"$DIR"/genStdTaskJson.py $@`"
  if [ $? -eq 0 ]
  then
    echo "$JSON" | "$DIR"/../../taskgrader.py | "$DIR"/summarizeResults.py
  fi
else
  "$DIR"/genStdTaskJson.py -h
fi  
