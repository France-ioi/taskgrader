#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This tool runs a series of tests against the taskgrader to check its behavior
# is as expected and the local configuration is good.


import argparse, json, os, subprocess, sys

# Path to the taskgrader executable
CFG_TASKGRADER = os.path.normpath(os.path.dirname(os.path.abspath(__file__)) + '/../taskgrader.py')


class FullTestBase(object):
    """A full test is a test sending a full evaluation JSON to the taskgrader,
    and checking whether the outputJson returns expected results."""

    def __init__(self):
        self.details = {}

    def _assertEqual(self, varName, assertedValue):
        """Tests whether the variable pointed by self.`varName` is equal to
        assertedValue."""
        try:
            var = eval("self." + varName)
        except:
            self.details['bad'].append('`%s` does not exist (should be equal to `%s`)' % (varName, assertedValue))
            return False

        if isinstance(var, basestring):
            var = var.strip()
            assertedValue = assertedValue.strip()

        if var == assertedValue:
            self.details['good'].append('`%s` == `%s`' % (varName, assertedValue))
            return True
        else:
            self.details['bad'].append('`%s` != `%s`' % (varName, assertedValue))
            return False

    def _makeInputJson(self):
        """Makes the data to be sent to the taskgrader."""

        raise Exception("_makeInputJson must be overloaded.")

    def _makeChecks(self):
        """Return the list of check resulsts."""

        raise Exception("_makeChecks must be overloaded.")

    def _isCorrect(self):
        """Checks whether the results correspond to expectations."""

        checkList = self._makeChecks()
        good = len(filter(None, checkList))
        bad = len(checkList) - good

        if bad > 0:
            self.details['msg'] = 'Test failed, %d checks good, %d checks bad.' % (good, bad)
            return False
        else:
            self.details['msg'] = 'Test passed, %d checks good.' % good
            return True

    def execute(self):
        """Execute the test and returns whether the test was passed or not.
        self.details contains more details for debug."""

        self.inputJson = self._makeInputJson()
        self.proc = subprocess.Popen(['/usr/bin/python2', CFG_TASKGRADER], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (self.procOut, self.procErr) = self.proc.communicate(input=json.dumps(self.inputJson))
        self.details = {'stdout': self.procOut,
                'stderr': self.procErr,
                'returncode': self.proc.returncode,
                'good': [], # Will contain good assertions
                'bad': []}  # Will contain bad assertions
        try:
            self.outputJson = json.loads(self.procOut)
            self.details['validjson'] = True
        except:
            self.details['validjson'] = False
        self.result = self._isCorrect()
        return self.result


class SanitizerCheckerTest(FullTestBase):
    """This test only sends a sanitizer and a checker to compile; the expected
    behavior is to have the taskgrader compile them and then exit successfully
    without evaluating any solution."""


    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': [],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': [],
            'executions': []
            }

    def _makeChecks(self):
        return [
            self._assertEqual("proc.returncode", 0),
            self._assertEqual("outputJson['sanitizer']['exitCode']", 0),
            self._assertEqual("outputJson['checker']['exitCode']", 0)
            ]

class BadSanitizerTest(FullTestBase):
    """This test sends a bad sanitizer which cannot compile; the taskgrader is
    expected to exit with an error after being unable to compile the
    sanitizer."""

    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': [],
            'sanitizer': '@testBadProgram',
            'checker': '@testChecker',
            'solutions': [],
            'executions': []
            }

    def _makeChecks(self):
        return [
            self._assertEqual("proc.returncode", 1),
            ]

class BadCheckerTest(FullTestBase):
    """This test sends a bad checker which cannot compile; the taskgrader is
    expected to exit with an error after being unable to compile the
    checker."""

    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': [],
            'sanitizer': '@testSanitizer',
            'checker': '@testBadProgram',
            'solutions': [],
            'executions': []
            }

    def _makeChecks(self):
        return [
            self._assertEqual("proc.returncode", 1)
            ]

class GenerationSingleTest(FullTestBase):
    """This test uses a simple generator, and checks whether it is executed
    successfully."""

    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': ['@testGenerator1'],
            'generations': ['@testGenerationSingle'],
            'extraTests': [],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': [],
            'executions': []
            }

    def _makeChecks(self):
        return [
            self._assertEqual("proc.returncode", 0),
            self._assertEqual("outputJson['generators'][0]['compilationExecution']['exitCode']", 0),
            self._assertEqual("outputJson['generations'][0]['generatorExecution']['exitCode']", 0)
            ]

class GenerationCasesTest(FullTestBase):
    """This test uses the "testCases" feature: it generates an input test file
    and the expected output with a couple generator + output generator."""

    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': ['@testGenerator2', '@testGenerator2out'],
            'generations': ['@testGenerationCases'],
            'extraTests': [],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': [],
            'executions': []
            }

    def _makeChecks(self):
        return [
            self._assertEqual("proc.returncode", 0),
            self._assertEqual("outputJson['generators'][0]['compilationExecution']['exitCode']", 0),
            self._assertEqual("outputJson['generators'][1]['compilationExecution']['exitCode']", 0),
            self._assertEqual("outputJson['generations'][0]['generatorExecution']['exitCode']", 0),
            self._assertEqual("outputJson['generations'][0]['outputGeneratorExecution']['exitCode']", 0),
            self._assertEqual("outputJson['generations'][0]['generatorExecution']['stdout']['data']", "20"),
            self._assertEqual("outputJson['generations'][0]['outputGeneratorExecution']['stdout']['data']", "40"),
            ]

class SolutionSimpleTest(FullTestBase):
    """This test tries a simple solution execution, with one test file, and
    checks the checker output."""

    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolution1'],
            'executions': ['@testExecution1']
            }

    def _makeChecks(self):
        return [
            self._assertEqual("proc.returncode", 0),
            self._assertEqual("outputJson['executions'][0]['testsReports'][0]['checker']['stdout']['data']", "100")
            ]

class SolutionInvalidTest(FullTestBase):
    """This test tries an invalid solution (giving a wrong result), with one
    test file, and checks the checker output."""

    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolutionInvalid'],
            'executions': ['@testExecutionInvalid']
            }

    def _makeChecks(self):
        return [
            self._assertEqual("proc.returncode", 0),
            self._assertEqual("outputJson['executions'][0]['testsReports'][0]['checker']['stdout']['data']", "0")
            ]

class SolutionUncompTest(FullTestBase):
    """This test tries a bad solution which cannot be compiled."""

    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolutionUncomp'],
            'executions': ['@testExecutionUncomp']
            }

    def _makeChecks(self):
        return [
            self._assertEqual("proc.returncode", 0),
            self._assertEqual("outputJson['solutions'][0]['compilationExecution']['exitCode']", 1)
            ]

class SolutionMemoverflowTest(FullTestBase):
    """This test tries a solution using more memory than the allowed limit."""

    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolutionMemoverflow'],
            'executions': ['@testExecutionMemoverflow']
            }

    def _makeChecks(self):
        return [
            self._assertEqual("proc.returncode", 0),
            self._assertEqual("outputJson['executions'][0]['testsReports'][0]['execution']['exitCode']", 1),
            self._assertEqual("outputJson['executions'][0]['testsReports'][0]['execution']['exitSig']", 11)
            ]

class SolutionTimeoutTest(FullTestBase):
    """This test tries a solution using more time than the allowed limit."""

    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolutionTimeout1', '@testSolutionTimeout2'],
            'executions': ['@testExecutionTimeout1', '@testExecutionTimeout2']
            }

    def _makeChecks(self):
        return [
            self._assertEqual("proc.returncode", 0),
            self._assertEqual("outputJson['executions'][0]['testsReports'][0]['execution']['exitCode']", 1),
            self._assertEqual("outputJson['executions'][0]['testsReports'][0]['execution']['exitSig']", 137),
            self._assertEqual("outputJson['executions'][1]['testsReports'][0]['execution']['exitCode']", 1),
            self._assertEqual("outputJson['executions'][1]['testsReports'][0]['execution']['exitSig']", 137)
            ]

class SolutionChangingTest(FullTestBase):
    """This test tries executing a solution (whose output changes) twice and
    checks whether its result has correctly been cached."""

    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolutionChanging'],
            'executions': ['@testExecutionChanging1', '@testExecutionChanging2']
            }

    def _makeChecks(self):
        checks = [
            self._assertEqual("proc.returncode", 0),
            ]
        try:
            output1 = self.outputJson['executions'][0]['testsReports'][0]['execution']['stdout']['data']
        except:
            self.details['bad'].append("can't get output from first execution")
            checks.append(False)
            return checks
        try:
            output2 = self.outputJson['executions'][1]['testsReports'][0]['execution']['stdout']['data']
        except:
            self.details['bad'].append("can't get output from second execution")
            checks.append(False)
            return checks
        if output1 == output2:
            self.details['good'].append("output1 == output2")
        else:
            self.details['bad'].append("output1 != output2")
        checks.append(output1 == output2)
        return checks

class TestMultipleTest(FullTestBase):
    """This test tries a simple solution with multiple test files, and checks
    the solution and the checker output."""

    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1', '@testExtraSimple2', '@testExtraSimple3'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolution1'],
            'executions': ['@testExecution1']
            }

    def _makeChecks(self):
        return [
            self._assertEqual("proc.returncode", 0),
            self._assertEqual("outputJson['executions'][0]['testsReports'][0]['execution']['stdout']['data']", "60"),
            self._assertEqual("outputJson['executions'][0]['testsReports'][0]['checker']['stdout']['data']", "100"),
            self._assertEqual("outputJson['executions'][0]['testsReports'][1]['execution']['stdout']['data']", "90"),
            self._assertEqual("outputJson['executions'][0]['testsReports'][1]['checker']['stdout']['data']", "100"),
            self._assertEqual("outputJson['executions'][0]['testsReports'][2]['execution']['stdout']['data']", "384"),
            self._assertEqual("outputJson['executions'][0]['testsReports'][2]['checker']['stdout']['data']", "100")
            ]



if __name__ == '__main__':
    # TODO :: interface
    tests = [
        SanitizerCheckerTest(),
        BadSanitizerTest(),
        BadCheckerTest(),
        GenerationSingleTest(),
        GenerationCasesTest(),
        SolutionSimpleTest(),
        SolutionInvalidTest(),
        SolutionUncompTest(),
        #SolutionMemoverflowTest(), # not working at the moment
        SolutionTimeoutTest(),
        SolutionChangingTest(),
        TestMultipleTest()
        ]
    for t in tests:
        t.execute()
        print "%s: %s (%s): %s" % (t.__class__.__name__, t.result, t.details['msg'], t.details['bad'])
        if not t.result:
            print t.procOut
            print t.procErr

    # Test restrictToPaths
    # Test all languages
