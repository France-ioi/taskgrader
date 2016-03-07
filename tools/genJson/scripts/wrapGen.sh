#!/bin/bash
mkdir files
mkdir wrapgen
mv generators.py libRobot.py Makefile $TASKGRADER_DEPFILES wrapgen/ 2> /dev/null
cd wrapgen/
sh gen.sh
if cd ../files/
then for FILE in `find -type f`
  do
    NEWNAME=`echo "$FILE" | sed 's/^..//' | sed 's/\//-/g' | sed 's/^lib-//'`
    mv "$FILE" "../$NEWNAME"
  done
fi
