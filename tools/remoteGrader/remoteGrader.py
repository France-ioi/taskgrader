#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

import argparse, json, sys, time, urllib.request, urllib.parse
from config import *

API = CFG_API
USERNAME = CFG_USERNAME
PASSWORD = CFG_PASSWORD

def printErr(msg):
    """Print a message on stderr."""
    sys.stderr.write(msg)
    sys.stderr.flush()

def apiRequest(request):
    """Make a request to the API."""
    postdata = urllib.parse.urlencode({
        'rRequest': json.dumps(request),
        'rUsername': USERNAME,
        'rPassword': PASSWORD
        })
    post = urllib.request.urlopen(API, postdata.encode('ascii'))
    resp = post.read().decode('utf-8')
    try:
        resp = json.loads(resp)
    except:
        raise Exception("graderqueue answered non-JSON data to request '%s': `%s`.\nCannot proceed." % (request['request'], resp))

    return resp

def checkApiOk(response):
    """Check the error code from an API answer."""
    try:
        errorCode = response['errorcode']
    except:
        return False
    return (errorCode == 0)


def displayApiError(response, request=None):
    """Display an error from an API answer."""
    if request:
        printErr("graderqueue responded request '%s' with error #%s: %s\n" % (
            request,
            response.get('errorcode', '?'),
            response.get('errormsg', '[no error message]')))
    else:
        printErr("graderqueue responded error #%s: %s\n" % (
            response.get('errorcode', '?'),
            response.get('errormsg', '[no error message]')))


def sendJob(inputJson, jobname='remotetest'):
    """Send a job to the graderqueue."""
    request = {
        'request': 'sendjob',
        'priority': 1,
        'tags': '',
        'jobname': jobname,
        'jobdata': json.dumps(inputJson)
    }

    return apiRequest(request)


def getJob(jobid):
    """Fetch information about a job."""
    request = {
        'request': 'getjob',
        'jobid': jobid
        }

    return apiRequest(request)

def getJobLoop(jobid, display=False):
    """Wait for completion of a job and return its data."""
    if display:
        printErr("Waiting for evaluation")
    start_time = time.time()

    isSent = False

    while time.time() - start_time < CFG_TIMEOUT:
        if display:
            printErr('.')
        jobReq = getJob(jobid)

        # We ignore errors, they can be temporary
        try:
            if jobReq['origin'] == 'done':
                # Job is done
                break

            # TODO :: show if task in queue has an error or something

            if not isSent and jobReq['data']['status'] == 'sent':
                # Job was sent to a server
                if display:
                    printErr("\nEvaluation in progress")
                isSent = True
                # We refresh the timer
                start_time = time.time()
        except:
            pass
        time.sleep(1)

    if display:
        printErr("\n")

    return jobReq


def gradeJob(inputJson):
    """Send a job and fetch results."""
    printErr("Sending job...")
    sendReq = sendJob(inputJson)

    if not checkApiOk(sendReq):
        printErr("\n")
        displayApiError(sendReq, request='sendjob')
        sys.exit(1)

    jobid = int(sendReq['jobid'])
    printErr(" queued successfully as id #%d.\n" % jobid)

    jobReq = getJobLoop(jobid, display=True)
    if not checkApiOk(jobReq):
        displayApiError(jobReq)
        sys.exit(1)

    if jobReq['origin'] == 'queue':
        printErr("Task wasn't evaluated in %d seconds.\n" % CFG_TIMEOUT)
        printErr("Use `remoteGrader.py -g %d` to try again to fetch results.\n" % jobid)
        sys.exit(1)

    return json.loads(jobReq['data']['resultdata'])['jobdata']


def testAuth():
    """Test the authentication."""
    req = apiRequest({'request': 'test'})
    if not checkApiOk(req):
        displayApiError(req)
        return False
    printErr(req['errormsg']+"\n")
    return True


def interactiveConfig():
    """Configure interactively."""
    # TODO


if __name__ == '__main__':
    argParser = argparse.ArgumentParser(description="Launches an evaluation with a remote taskgrader through the graderqueue.")
    argParser.add_argument('file', metavar='FILE', nargs='?', help='Input JSON file.', default='')
    # TODO :: add options: test, getjob, ...
    args = argParser.parse_args()

    # By default, we make the paths given on command-line absolute
    if args.file:
        try:
            inputJson = json.load(open(args.file, 'r'))
        except:
            raise Exception("File `%s` does not contain valid JSON data." % args.file)
    else:
        try:
            inputJson = json.load(sys.stdin)
        except:
            raise Exception("No valid JSON data received on standard input.")

    resultdata = gradeJob(inputJson)
    print(json.dumps(resultdata))
