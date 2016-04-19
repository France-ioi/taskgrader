#!/bin/bash

### Install script for the taskgrader
# Checks for program dependencies and compiles required programs

# TODO :: rework this script

### Check for dependencies
ERROR=0
echo "*** Checking for required binaries..."
for BINARY in python python2.7
do
    if which $BINARY > /dev/null
    then
        echo "$BINARY detected."
    else
        echo "[ERROR] $BINARY missing, please install it before continuing."
        ERROR=1
    fi
done
if [ $ERROR -eq 1 ]
then
    echo "[ERROR] Some binaries are missing. Please install them before continuing."
    exit 1
fi

echo
echo "*** Checking for optional binaries..."
for BINARY in fpc g++ gcc gcj git nodejs ocamlopt php5 python3
do
    if which $BINARY > /dev/null
    then
        echo "$BINARY detected."
    else
        echo "[Warning] $BINARY missing, some features won't work properly."
        ERROR=2
    fi
done
if [ $ERROR -eq 2 ]
then
    echo "[Warning] Some optional binaries missing, some features won't work properly."
fi

### Fetch jsonschema and moe
echo
echo "*** Fetching dependencies..."
if which git > /dev/null
then
    git submodule update --init Jvs2Java jsonschema isolate

    ### Compile Jvs2Java
    if which gcj > /dev/null
    then
        echo
        echo "*** Compiling Jvs2Java..."
        gcj --encoding=utf8 --main=Jvs2Java -o jvs2java Jvs2Java/Jvs2Java.java
    else
        echo "[Warning] gcj missing, cannot compile Jvs2Java."
        echo "          Languages 'java' and 'javascool' will not be available."
        ERROR=2
    fi
else
    echo "[Warning] git not present, cannot fetch and compile dependencies"
    echo "          isolate, jsonschema, Jvs2Java. Some features will be unavailable."
    ERROR=2
fi

if which git > /dev/null && which sudo > /dev/null
then
  echo
  echo "*** Installing isolate"
  read -p "[?] Install isolate (needs root privileges)? [y/n]" -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]
  then
    ### Compile isolate
    echo "* Compiling isolate..."
    make -C isolate isolate
    mv isolate/isolate isolate-bin

    ### Compile C programs
    echo "* Setting isolate-bin rights..."
    if ! sudo chown root:root isolate-bin
    then
        echo "[ERROR] Failed to \`chown root:root isolate-bin\`. Please run the command as root."
        ERROR=1
    fi

    if ! sudo chmod 4755 isolate-bin
    then
        echo "[ERROR] Failed to \`chmod 4755 isolate-bin\`. Please run the command as root."
        ERROR=1
    fi
    echo "* Compiling box-rights..."
    if gcc -O3 -o box-rights box-rights.c
    then
        echo "Box-rights successfully compiled."
        if ! sudo chown root:root box-rights
        then
            echo "[ERROR] Failed to \`chown root:root box-rights\`. Please run the command as root."
            ERROR=1
        fi
        if ! sudo chmod 4755 box-rights
        then
            echo "[ERROR] Failed to \`chmod 4755 box-rights\`. Please run the command as root."
            ERROR=1
        fi
    else
        echo "/!\ Error while compiling box-rights."
        ERROR=1
    fi
  else
    echo "Not installing isolate. Isolated execution will not be used."
  fi
else
    echo "[Warning] sudo not present, cannot fetch and compile isolate."
    echo "          Isolated execution will not be used."
    ERROR=2
fi

### Initialize data directories
echo
echo "*** Initializing (or resetting) data directories..."
if [ -d files ]
then
  # We reset the data folder, but do not delete it as a safety measure
  OLDFILES="files.`date +%F_%H-%M-%S`"
  echo "[Notice] Data folder 'files' already exists, moving it to"
  echo "         'oldfiles/$OLDFILES'."
  echo "         If you don't need anything from this folder, you can delete it safely."
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
  echo "[Notice] config.py detected, no new config.py file written."
fi

### Initialize genJson config.py
if ! [ -f tools/genJson/config.py ]
then
  cp -p tools/genJson/config.py.template tools/genJson/config.py
else
  echo "[Notice] genJson config.py detected, no new config.py file written."
fi

### Initialize stdGrade config.py
if ! [ -f tools/stdGrade/config.py ]
then
  cp -p tools/stdGrade/config.py.template tools/stdGrade/config.py
else
  echo "[Notice] stdGrade config.py detected, no new config.py file written."
fi

echo
echo "****************************************"
echo

if [ $ERROR -eq 1 ]
then
  echo "/!\ Installation errors occured, the taskgrader will not work properly."
  exit 1
elif [ $ERROR -eq 2 ]
then
  echo "Installation complete."
  echo "Some warnings occured, please check them before continuing."
  echo "The taskgrader will still work but some features might not behave properly."
  exit 0
else
  echo "Installation complete."
  exit 0
fi

