#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This companion tool to the taskgrader summarizes the output from the
# taskgrader. It reads the output JSON from stdin.

import json, os, sys

if __name__ == '__main__':
    # Read stdin
    inputData = sys.stdin.read()

    try:
        resultJson = json.loads(inputData)
    except:
        print 'Error: no valid JSON data read from stdin. Received:'
        print inputData
        sys.exit(1)

    for execution in resultJson['executions']:
        print ' * Execution %s:' % execution['name']
        for report in execution['testsReports']:
            if report.has_key('checker'):
                # Everything was executed
                print 'Solution executed successfully. Checker report:'
                print report['checker']['stdout']['data']
            elif report.has_key('execution'):
                # Solution error
                print 'Solution returned an error. Solution report:'
                print json.dumps(report['execution'])
            else:
                # Sanitizer error
                print 'Test rejected by sanitizer. Sanitizer report:'
                print json.dumps(report['sanitizer'])
