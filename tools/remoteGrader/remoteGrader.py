#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

import argparse, json, sys, time, urllib.request, urllib.parse
from remote_config import *

def printErr(msg):
    """Print a message on stderr."""
    sys.stderr.write(msg)
    sys.stderr.flush()

def apiRequest(request):
    """Make a request to the API."""
    postdata = urllib.parse.urlencode({
        'rRequest': json.dumps(request),
        'rUsername': CFG_USERNAME,
        'rPassword': CFG_PASSWORD
        })
    post = urllib.request.urlopen(CFG_API, postdata.encode('ascii'))
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


def sendJob(inputJson, jobname='remotetest', revision=None):
    """Send a job to the graderqueue."""
    request = {
        'request': 'sendjob',
        'priority': 1,
        'tags': '',
        'jobname': jobname,
        'jobdata': json.dumps(inputJson)
    }
    if revision is not None:
        request['taskrevision'] = revision

    return apiRequest(request)


def getJob(jobid):
    """Fetch information about a job."""
    request = {
        'request': 'getjob',
        'jobid': jobid
        }

    return apiRequest(request)

def getJobLoop(jobid, display=False, exit=False):
    """Wait for completion of a job and return its data.
    display activates displaying information, exit will exit if the task wasn't
    evaluated (implies display)."""
    if exit:
        display = True
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

    if exit:
        if not checkApiOk(jobReq):
            displayApiError(jobReq)
            sys.exit(1)

        if jobReq['origin'] == 'queue':
            printErr("Task wasn't evaluated in %d seconds.\n" % CFG_TIMEOUT)
            printErr("Use the option '-g %d' to try again fetching results.\n" % jobid)
            sys.exit(1)

    return jobReq


def gradeJob(inputJson, revision=None):
    """Send a job and fetch results."""
    # Send job
    printErr("Sending job...")
    sendReq = sendJob(inputJson, revision=revision)

    if not checkApiOk(sendReq):
        printErr("\n")
        displayApiError(sendReq, request='sendjob')
        sys.exit(1)

    # Success
    jobid = int(sendReq['jobid'])
    printErr(" queued successfully as id #%d.\n" % jobid)

    # Fetch results
    jobReq = getJobLoop(jobid, exit=True)
    return json.loads(jobReq['data']['resultdata'])['jobdata']


def testAuth():
    """Test the authentication."""
    req = apiRequest({'request': 'test'})
    if not checkApiOk(req):
        printErr("Test failed: ")
        displayApiError(req)
        return False
    printErr("Success: %s\n" % req['errormsg'])
    return True


if __name__ == '__main__':
    argParser = argparse.ArgumentParser(description="Launches an evaluation with a remote taskgrader through the graderqueue.")
    argParser.add_argument('-g', '--getjob', help="Try again to fetch results of ID", action='store', metavar='ID', type=int)
    argParser.add_argument('-r', '--revision', help="Tell the queue which task revision is needed", action='store', metavar='REV')
    argParser.add_argument('-t', '--test', help="Test connection to the graderqueue", action='store_true')
    argParser.add_argument('file', metavar='FILE', nargs='?', help='Input JSON file.', default='')
    args = argParser.parse_args()

    if not (CFG_API and CFG_USERNAME and CFG_PASSWORD):
        printErr("API and credentials for remoteGrader not configured.\n")
        printErr("Please edit `remote_config.py` in `tools/remoteGrader` folder.\n")
        sys.exit(1)

    # Test connection
    if args.test:
        if testAuth():
            sys.exit(0)
        else:
            sys.exit(1)

    # Try again fetching a previously sent job
    if args.getjob:
        jobReq = getJobLoop(args.getjob, exit=True)
        resultdata = json.loads(jobReq['data']['resultdata'])['jobdata']
        json.dump(resultdata, sys.stdout)
        sys.exit(0)

    # If no file is given, we load from stdin
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

    resultdata = gradeJob(inputJson, revision=args.revision)
    json.dump(resultdata, sys.stdout)
