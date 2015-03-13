#!/bin/bash

### Install script for the taskgrader
# Checks for program dependencies and compiles required programs

### Check for dependencies
ERROR=0
for BINARY in gcc g++ python2 python3 shar
do
    if which $BINARY > /dev/null
    then
        echo "$BINARY detected."
    else
        echo "$BINARY missing, please install it before continuing."
        ERROR=1
    fi
done
if [ $ERROR -eq 1 ]
then
    echo "Some binaries are missing. Please install them before continuing."
    exit 1
fi

### Compile C programs
# TODO :: isolate needs autoconf.h + probably other things
if gcc -O3 -o isolate isolate.c
then
    echo "Isolate successfully compiled."
    if ! chmod 4755 isolate
    then
        echo "Failed to \`chmod 4755 isolate\`. Please run the command as root."
        ERROR=1
    fi
    if ! chown root:root isolate
    then
        echo "Failed to \`chown root:root isolate\`. Please run the command as root."
        ERROR=1
    fi
else
    echo "Error while compiling isolate."
    ERROR=1
fi

if gcc -O3 -o box-rights box-rights.c
then
    echo "Box-rights successfully compiled."
    if ! chown root:root box-rights
    then
        echo "Failed to \`chown root:root box-rights\`. Please run the command as root."
        ERROR=1
    fi
    if ! chmod 4755 box-rights
    then
        echo "Failed to \`chmod 4755 box-rights\`. Please run the command as root."
        ERROR=1
    fi
else
    echo "Error while compiling box-rights."
    ERROR=1
fi

if [ $ERROR -eq 1 ]
then
    echo "Installation errors occured, please check them before continuing."
    exit 1
fi

echo "Install completed successfully!"
exit 0
