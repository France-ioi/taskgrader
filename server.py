#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT



import getopt, json, os, requests, string, sys, subprocess, time
import urllib, urllib2, urllib2_ssl
from config import CFG_TASKGRADER, CFG_GRADERQUEUE_POLL, CFG_GRADERQUEUE_SEND, CFG_GRADERQUEUE_ROOT, CFG_GRADERQUEUE_VARS, CFG_GRADERQUEUE_CLIENTCERT


def usage():
    print """Usage: server.py [option]...
Launches an evaluation server.

 -d, --debug        Shows all the JSON data in and out (implies -v)
 -D, --daemon       Daemonize the process (incompatible with -v)
 -h, --help         Shows this usage information
 -v, --verbose      Gives some information on standard output"""


if __name__ == '__main__':
    daemon = False
    debug = False
    verbose = False

    # Read command line options
    try:
        (opts, extraargs) = getopt.getopt(sys.argv[1:], 'dDhv', ['daemon', 'debug', 'help', 'verbose'])
    except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(1)

    for (opt, arg) in opts:
        if opt in ['-d', '--debug']:
            debug = True
            verbose = True
        elif opt in ['-D', '--daemon']:
            daemon = True
        elif opt in ['-h', '--help']:
            usage()
            sys.exit(0)
        elif opt in ['-v', '--verbose']:
            verbose = True

    if daemon and verbose:
        print "Can't daemonize while verbose mode is enabled."
        usage()
        sys.exit(1)


    if daemon:
        # Daemonize
        if os.fork() > 0:
            sys.exit(0)
        os.chdir("/")
        os.setsid()
        os.umask(0)
        if os.fork() > 0:
            sys.exit(0)

    lastTaskTime = time.time()

    while(time.time()-lastTaskTime < 60):
        # Main loop

        # We wait 1 second between each poll request
        time.sleep(1)

        # Request data from the taskqueue
        opener = urllib2.build_opener(urllib2_ssl.HTTPSHandler(
            key_file=CFG_GRADERQUEUE_KEY, cert_file=CFG_GRADERQUEUE_CERT, ca_certs=CFG_GRADERQUEUE_CA, checker=lambda x, y: True))
        r = opener.open(CFG_GRADERQUEUE_POLL).read()
        try:
            jsondata = json.loads(r)
        except:
            print 'Error: Taskqueue returned non-JSON data.'
            print r
            sys.exit(1)

        if not jsondata.has_key('errorcode'):
            print 'Error: Taskqueue returned data without errorcode.'
            sys.exit(1)

        start_time = time.clock()

        # Handle various possible errors
        if jsondata['errorcode'] == 1:
            if verbose:
                print 'Taskqueue has no available task.'
            continue
        elif jsondata['errorcode'] == 2:
            print 'Error: Taskqueue returned an error (%s)' % jsondata['errormsg']
            sys.exit(1)
        elif jsondata['errorcode'] != 0:
            print 'Error: Taskqueue returned an unknown errorcode (%s)' % jsondata['errorcode']
            sys.exit(1)
        elif not (jsondata.has_key('taskdata') and jsondata.has_key('taskname') and jsondata.has_key('taskid')):
            print 'Error: Taskqueue returned no taskdata.'
            sys.exit(1)

        lastTaskTime = time.time()

        taskdata = jsondata['taskdata']
        if verbose:
            print 'Received task %s (#%d)' % (jsondata['taskname'], jsondata['taskid'])

        taskdata['rootPath'] = CFG_GRADERQUEUE_ROOT
        if taskdata.has_key('restrictToPaths'):
            taskdata['restrictToPaths'] = map(lambda p: Template(p).safe_substitute(CFG_GRADERQUEUE_VARS), taskdata['restrictToPaths'])

        if debug:
            print ''
            print '* JSON sent to taskgrader:'
            print json.dumps(taskdata)
    
        # Send to taskgrader
        if debug:
            print ''
            print '* Output from taskgrader'
        proc = subprocess.Popen(['/usr/bin/python', CFG_TASKGRADER], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (procOut, procErr) = proc.communicate(input=json.dumps(taskdata))

        if debug:
            print ''
            print '* Results'

        # Read taskgrader output
        try:
            evalJson = json.loads(procOut)
        except:
            evalJson = None

        if evalJson:
            if verbose:
                print "Execution successful."
            if debug:
                for execution in evalJson['executions']:
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
            if debug:
                print ''
                print '* Full report:'
                print json.dumps(evalJson)

            # Send back results
            resp = opener.open(CFG_GRADERQUEUE_SEND, data=urllib.urlencode(
                    {'taskid': jsondata['taskid'],
                     'resultdata': json.dumps({'errorcode': 0, 'taskdata': evalJson})})).read()

            if verbose:
                print "Sent results."
        else:
            if verbose:
                print "Taskgrader error."
            if debug:
                print "stdout:"
                print procOut
                print ""
                print "stderr:"
                print procErr

            resp = opener.open(CFG_GRADERQUEUE_SEND, data=urllib.urlencode(
                    {'taskid': jsondata['taskid'],
                     'resultdata': json.dumps({'errorcode': 2, 'errormsg': "stdout:\n%s\nstderr:\n%s" % (procOut, procErr)})})).read()

        try:
            respjson = json.loads(resp)
            if verbose:
                print "Taskqueue response: (%d) %s" % (respjson['errorcode'], respjson['errormsg'])
        except:
            print "Error: Taskqueue answered results with invalid data (%s)" % resp
            sys.exit(1)

    print "No task available, sleeping."
