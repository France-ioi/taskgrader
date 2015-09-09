#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This companion tool to the taskgrader makes a default evaluation JSON for the
# program(s) in FILE(s), using default parameters set in config.py.


import argparse, json, os, subprocess, sys
#from config import *

CFG_TASKGRADER = '/home/michel/franceioi/taskgrader/taskgrader.py'

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
    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple'],
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
    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple'],
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
    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple'],
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
    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple'],
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
    def _makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolutionTimeout'],
            'executions': ['@testExecutionTimeout']
            }

    def _makeChecks(self):
        return [
            self._assertEqual("proc.returncode", 0),
            self._assertEqual("outputJson['executions'][0]['testsReports'][0]['execution']['exitCode']", 1),
            self._assertEqual("outputJson['executions'][0]['testsReports'][0]['execution']['exitSig']", 137)
            ]



if __name__ == '__main__':
    tests = [SanitizerCheckerTest(), BadSanitizerTest(), BadCheckerTest(), GenerationSingleTest(), GenerationCasesTest(), SolutionSimpleTest(), SolutionInvalidTest(), SolutionUncompTest(), SolutionMemoverflowTest(), SolutionTimeoutTest()]
    for t in tests:
        t.execute()
        print "%s: %s (%s): %s" % (t.__class__.__name__, t.result, t.details['msg'], t.details['bad'])
        if not t.result:
            print t.procOut
            print t.procErr

    # Test restrictToPaths
    # Test random-outputing solutions w/ cache
    # Test all languages
