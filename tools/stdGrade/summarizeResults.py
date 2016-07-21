#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This companion tool to the taskgrader summarizes the output from the
# taskgrader. It reads the output JSON from stdin.

import json, os, sys

def summarizeOutput(output):
    outputLines = output.splitlines()
    if len(outputLines) > 7:
        print('\n'.join(outputLines[:3]))
        print('[... truncated ...]')
        print('\n'.join(outputLines[-3:]))
    else:
        print('\n'.join(outputLines))
    print('')

if __name__ == '__main__':
    # Read stdin
    inputData = sys.stdin.read()

    try:
        resultJson = json.loads(inputData)
    except:
        if inputData.strip() != '':
            print('Error: no valid JSON data read from stdin. Received:')
            print(inputData)
        sys.exit(1)

    # Summary
    summary = "Summary:"

    # Check how many solutions didn't compile
    lensolnok = len(list(filter(lambda x: x['compilationExecution']['exitCode'] != 0, resultJson['solutions'])))
    if lensolnok > 0:
        lensol = len(resultJson['solutions'])
        print(" * %d / %d solutions didn't compile properly:" % (lensolnok, lensol))
        summary += " %d failed compilation" % lensolnok
        for execution in resultJson['solutions']:
            if execution['compilationExecution']['exitCode'] != 0:
                print("-> Solution `%s` failed compilation, output:" % execution['id'])
                print("stdout: %s" % execution['compilationExecution']['stdout']['data'])
                print("stderr: %s" % execution['compilationExecution']['stderr']['data'])

    # Show executions information
    for execution in resultJson['executions']:
        print(' * Execution %s:' % execution['name'])
        suml = []
        for report in execution['testsReports']:
            if 'checker' in report:
                # Everything was executed
                print('Solution `%s` executed successfully on test `%s`. Checker report:' % (execution['name'], report['name']))
                checkerOut = report['checker']['stdout']['data']
                summarizeOutput(checkerOut)
                if checkerOut:
                    suml.append(checkerOut.splitlines()[0])
            elif 'execution' in report:
                # Solution error
                print('Solution `%s` returned an error on test `%s`. Solution report:' % (execution['name'], report['name']))
                print(json.dumps(report['execution']))
                suml.append('error')
            else:
                # Sanitizer error
                print('Test `%s` rejected by sanitizer. Sanitizer report:' % report['name'])
                print(json.dumps(report['sanitizer']))
                suml.append('reject')
        summary += "\n%s: %s" % (execution['name'], ', '.join(suml))

    print(summary)
