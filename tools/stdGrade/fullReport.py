#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This companion tool to the taskgrader prints an evaluation report in a
# human-readable form.

import json, os, sys


def showCaptureReport(report):
    """Print a captureReport."""
    print("""File `%(name)s`: (size %(sizeKb)dKb, truncated: %(wasTruncated)s)
`%(data)s`""" % report)


def showExecutionReport(originalReport, name='program'):
    """Print an executionReport."""
    # Fill non-required fields with default values
    report = {
        "memoryUsedKb": -1,
        "exitSig": -1,
        "continueOnError": False,
        "stdout": {'data': ''},
        "stderr": {'data': ''},
        "files": []
        }

    report.update(originalReport)

    # Make summary string
    if report['exitCode'] == 0:
        success = 'success'
    else:
        if report['wasKilled'] or report['exitSig'] > 0:
            success = 'killed, exitcode %(exitCode)d, signal %(exitSig)d' % report
        else:
            success = 'failure, exitcode %d' % report['exitCode']
        if report['continueOnError']:
            success += ' (ignored)'

    # Execution information
    print("Execution %s: %s" % (name, success))
    print("""Cmd: %(commandLine)s
cached: %(wasCached)s / exit code %(exitCode)d, sig %(exitSig)d, continueOnError: %(continueOnError)s
Time: %(timeTakenMs)gms (real %(realTimeTakenMs)gms, limit %(timeLimitMs)gms) / memory: %(memoryUsedKb)gKb (limit %(memoryLimitKb)gKb)""" % report)

    # Stdout / stderr
    if report['stdout']['data']:
        showCaptureReport(report['stdout'])
    if report['stderr']['data']:
        showCaptureReport(report['stderr'])
    if not report['stdout']['data'] and not report['stderr']['data']:
        print("no output")

    # Captured files
    if len(report['files']) > 0:
        print("Files captured:")
        for fileReport in report['files']:
            showCaptureReport(fileReport)

    print('')


def showEvaluationReport(json):
    """Print a full evaluation report."""
    # Generators
    if len(json['generators']) > 0:
        print("* Generators compilation")
        for generator in json['generators']:
            showExecutionReport(generator['compilationExecution'], name="generator '%s' compilation" % generator['id'])

    # Generations
    if len(json['generations']) > 0:
        print("* Generations")
        for generation in json['generations']:
            showExecutionReport(generator['generatorExecution'], name="generation '%s'" % generation['id'])
            if 'outputGeneratorExecution' in generation:
                showExecutionReport(generator['outputGeneratorExecution'], name="output generation '%s'" % generation['id'])

    # Sanitizer and checker
    print("* Sanitizer and checker")
    showExecutionReport(json['sanitizer'], name='sanitizer compilation')
    showExecutionReport(json['checker'], name='checker compilation')

    # Solutions
    if len(json['solutions']) > 0:
        print("* Solutions compilation")
        for solution in json['solutions']:
            showExecutionReport(solution['compilationExecution'], name="solution '%s' compilation" % solution['id'])

    # Executions
    for execution in json['executions']:
        print("* Execution %(id)s (solution %(name)s)" % execution)
        if len(execution['testsReports']) == 0:
            print("No test report.")
            continue

        for testReport in execution['testsReports']:
            print("-> Test %s" % testReport['name'])
            showExecutionReport(testReport['sanitizer'], name="sanitizer on test '%s'" % testReport['name'])
            if 'execution' in testReport:
                showExecutionReport(testReport['execution'], name="solution '%s' on test '%s'" % (execution['name'], testReport['name']))
            else:
                print("Test rejected, solution not executed.")
            if 'checker' in testReport:
                showExecutionReport(testReport['checker'], name="checker on test '%s'" % testReport['name'])
            else:
                print("Solution returned an error, answer not checker.")


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

    showEvaluationReport(resultJson)
