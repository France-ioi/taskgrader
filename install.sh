#!/bin/bash

### Install script for the taskgrader
# Checks for program dependencies and compiles required programs

### Check for dependencies
ERROR=0
echo "*** Checking for required binaries..."
for BINARY in gcc gcj git python sudo
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

echo "*** Checking for optional binaries..."
for BINARY in fpc g++ python2 python3 shar
do
    if which $BINARY > /dev/null
    then
        echo "$BINARY detected."
    else
        echo "/!\ $BINARY missing, some languages won't compile properly."
        ERROR=1
    fi
done
if [ $ERROR -eq 1 ]
then
    echo "/!\ Some optional binaries missing, some languages won't compile properly."
fi

### Fetch jsonschema and moe
echo "*** Fetching dependencies..."
git submodule update --init Jvs2Java jsonschema isolate

### Compile Jvs2Java
echo "*** Compiling Jvs2Java..."
gcj --encoding=utf8 --main=Jvs2Java -o jvs2java Jvs2Java/Jvs2Java.java

### Compile isolate
echo "*** Compiling isolate..."
make -C isolate isolate
mv isolate/isolate isolate-bin

### Compile C programs
echo "*** Setting isolate-bin rights..."
if ! sudo chown root:root isolate-bin
then
    echo "/!\ Failed to \`chown root:root isolate-bin\`. Please run the command as root."
    ERROR=1
fi

if ! sudo chmod 4755 isolate-bin
then
    echo "/!\ Failed to \`chmod 4755 isolate-bin\`. Please run the command as root."
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

### Initialize data directories
echo "*** Initializing (or resetting) data directories..."
if [ -d files ]
then
  # We reset the data folder, but do not delete it as a safety measure
  OLDFILES="files.`date+%F_%H-%M-%S`"
  echo "/!\ Data folder 'files' already exists, moving it to 'oldfiles/$OLDFILES'."
  echo "If you don't need anything from this folder, you can delete it safely."
  mkdir -p oldfiles
  mv files "oldfiles/$OLDFILES"
fi
mkdir -p files
mkdir -p files/cache
mkdir -p files/builds

### Initialize database
# We use python to avoid depending on sqlite3 client binary
./schema_db.py

### Modify config.py
if ! [ -f config.py ]
then
  cp -p config.py.template config.py
  sed -i "s|^CFG_BASEDIR.*$|CFG_BASEDIR=\"`pwd`/files/\"|" config.py
  sed -i "s|^CFG_BINDIR.*$|CFG_BINDIR=\"`pwd`/\"|" config.py
else
  echo "/!\ config.py detected, no new config.py file written."
fi

### Initialize genJson config.py
if ! [ -f tools/genJson/config.py ]
then
  cp -p tools/genJson/config.py.template tools/genJson/config.py
else
  echo "/!\ genJson config.py detected, no new config.py file written."
fi

### Initialize stdGrade config.py
if ! [ -f tools/stdGrade/config.py ]
then
  cp -p tools/stdGrade/config.py.template tools/stdGrade/config.py
else
  echo "/!\ stdGrade config.py detected, no new config.py file written."
fi


if [ $ERROR -eq 1 ]
then
    echo "*** Installation errors occured, please check them before continuing."
    exit 1
fi

echo "*** Install completed successfully!"
exit 0
