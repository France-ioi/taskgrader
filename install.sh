#!/bin/bash

### Install script for the taskgrader
# Checks for program dependencies and compiles required programs

### Check for dependencies
ERROR=0
echo "*** Checking for required binaries..."
for BINARY in fpc gcc g++ gcj git python2 python3 shar sudo
do
    if which $BINARY > /dev/null
    then
        echo "$BINARY detected."
    else
        echo "/!\ $BINARY missing, please install it before continuing."
        ERROR=1
    fi
done
if [ $ERROR -eq 1 ]
then
    echo "/!\ Some binaries are missing. Please install them before continuing."
    exit 1
fi

### Fetch isolate
echo "*** Fetching isolate from git://git.ucw.cz/moe.git..."
git clone git://git.ucw.cz/moe.git
cd moe
./configure
make
mv obj/isolate/isolate ../
cd ..

### Compile C programs
echo "*** Setting isolate rights..."
if ! sudo chmod 4755 isolate
then
    echo "/!\ Failed to \`chmod 4755 isolate\`. Please run the command as root."
    ERROR=1
fi
if ! sudo chown root:root isolate
then
    echo "/!\ Failed to \`chown root:root isolate\`. Please run the command as root."
    ERROR=1
fi

echo "*** Compiling box-rights..."
if gcc -O3 -o box-rights box-rights.c
then
    echo "Box-rights successfully compiled."
    if ! sudo chown root:root box-rights
    then
        echo "/!\ Failed to \`chown root:root box-rights\`. Please run the command as root."
        ERROR=1
    fi
    if ! sudo chmod 4755 box-rights
    then
        echo "/!\ Failed to \`chmod 4755 box-rights\`. Please run the command as root."
        ERROR=1
    fi
else
    echo "/!\ Error while compiling box-rights."
    ERROR=1
fi

echo "*** Notice:"
echo "Please set, in taskgrader.py:"
echo "-the variable CFG_BASEDIR in taskgrader.py to an existing clean directory,"
echo " it will contain the builds and cache;"
echo "-the variable CFG_BINDIR in taskgrader.py to the directory containing the taskgrader"
echo " and the binaries compiled by this script;"
echo "in grade.py:"
echo "-the variable CFG_TASKGRADER to the path of taskgrader.py."

if [ $ERROR -eq 1 ]
then
    echo "*** Installation errors occured, please check them before continuing."
    exit 1
fi

echo "*** Install completed successfully!"
exit 0
