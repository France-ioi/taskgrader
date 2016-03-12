#!/bin/bash
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
if [ -n "$1" ]
then
  "$DIR"/genStdTaskJson.py $@ | "$DIR"/../../taskgrader.py | "$DIR"/summarizeResults.py
else
  "$DIR"/genStdTaskJson.py -h
fi  
