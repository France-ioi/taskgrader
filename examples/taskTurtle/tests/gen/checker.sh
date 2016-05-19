#!/bin/sh

/bin/chmod a+x checker.py turtleToPng.py
/usr/bin/xvfb-run -s '-screen 0 1280x1024x24' ./turtleToPng.py $1 > turtle_png.b64
"$TASKGRADERDIR"/tools/isolate-run.py -- ./checker.py $1 $2 $3
