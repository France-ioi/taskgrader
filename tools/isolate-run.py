#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This tool launches an isolated execution. It is intended as a wrapper around
# the execution of any command.

import argparse, os, sys

DEFAULT_EXECPARAMS = {
    'timeLimitMs': 60000,
    'memoryLimitKb': 128*1024,
    'useCache': False,
    'stdoutTruncateKb': -1,
    'stderrTruncateKb': -1,
    'getFiles': []
    }

# Add taskgrader folder to PATH
SELFDIR = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(SELFDIR, '../'))

from taskgrader import IsolatedExecution


if __name__ == '__main__':
    argParser = argparse.ArgumentParser(description="Makes a 'standalone' JSON file, bundling files referenced by path into the JSON to remove any reference to paths.")
    argParser.add_argument('-i', '--stdin', help='Set file to pass on stdin.')
    argParser.add_argument('-m', '--memory-limit', help='Set memory limit for execution, in kilobytes.', type=int)
    argParser.add_argument('-t', '--time-limit', help='Set time limit for execution, in milliseconds.', type=int)
    argParser.add_argument('-p', '--path', help='Set the working directory for the execution.', default='.')
    argParser.add_argument('args', nargs=argparse.REMAINDER)

    args = argParser.parse_args()

    # Check cmd line
    if not args.args:
        argParser.error("No command specified.")
    if '--' in args.args: args.args.remove('--')

    # Set up execution parameters
    execParams = {}
    execParams.update(DEFAULT_EXECPARAMS)
    if args.memory_limit: execParams['memoryLimitKb'] = args.memory_limit
    if args.time_limit: execParams['timeLimitMs'] = args.time_limit

    # Prepare files
    cmdLine = ' '.join(args.args)
    stdoutPath = os.path.join(args.path, 'isolate-run.stdout')

    # Launch the isolated execution
    execution = IsolatedExecution(None, execParams, cmdLine)
    report = execution.execute(args.path, stdinFile=args.stdin, stdoutFile=stdoutPath)

    sys.stdout.write(open(stdoutPath, 'r').read())
    sys.stderr.write(report['stderr']['data'])
    sys.exit(report['exitCode'])
