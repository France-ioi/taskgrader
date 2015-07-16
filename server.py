#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This script starts a server, fetching tasks from the graderqueue and sending
# them to the taskgrader.
# See https://github.com/France-ioi/graderqueue .


import argparse, json, os, requests, string, sys, subprocess, time
import urllib, urllib2, urllib2_ssl
from config import CFG_TASKGRADER, CFG_BASEDIR, CFG_SERVER_PIDFILE, CFG_GRADERQUEUE_POLL, CFG_GRADERQUEUE_SEND, CFG_GRADERQUEUE_ROOT, CFG_GRADERQUEUE_VARS, CFG_GRADERQUEUE_KEY, CFG_GRADERQUEUE_CERT, CFG_GRADERQUEUE_CA, CFG_GRADERQUEUE_CHECKER


if __name__ == '__main__':
    # Read command line options
    argParser = argparse.ArgumentParser(description="Launches an evaluation server for use with the graderQueue.")

    argParser.add_argument('-d', '--debug', help='Shows all the JSON data in and out (implies -v)', action='store_true')
    argParser.add_argument('-D', '--daemon', help='Daemonize the process (incompatible with -v)', action='store_true')
    argParser.add_argument('-s', '--server', help='Server mode: start only if not already started (implies -D)', action='store_true')
    argParser.add_argument('-v', '--verbose', help='Be more verbose', action='store_true')

    args = argParser.parse_args()

    args.verbose = args.verbose or args.debug
    args.daemon = args.daemon or args.server

    if args.daemon and args.verbose:
        print "Can't daemonize while verbose mode is enabled."
        argParser.print_help()
        sys.exit(1)


    if args.server:
        # Launch only if not already started
        try:
            pid = int(open(CFG_SERVER_PIDFILE, 'r').read())
        except:
            pid = 0
        if pid > 0:
            try:
                os.kill(pid, 0)
            except OSError as err:
                if err.errno == 1:
                    print "Server exists as another user. Exiting."
                    sys.exit(1)
            else:
                print "Server already launched. Exiting."
                sys.exit(1)

    if args.daemon:
        # Daemonize
        if os.fork() > 0:
            sys.exit(0)
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.chdir("/")
        os.setsid()
        os.umask(0)
        if os.fork() > 0:
            sys.exit(0)

    if args.server:
        # Write new PID
        open(CFG_SERVER_PIDFILE, 'w').write(str(os.getpid()))

    lastTaskTime = time.time()

    while(time.time()-lastTaskTime < 60):
        # Main loop

        # We wait 1 second between each poll request
        time.sleep(1)

        # Request data from the taskqueue
        opener = urllib2.build_opener(urllib2_ssl.HTTPSHandler(
            key_file=CFG_GRADERQUEUE_KEY,
            cert_file=CFG_GRADERQUEUE_CERT,
            ca_certs=CFG_GRADERQUEUE_CA,
            checker=CFG_GRADERQUEUE_CHECKER))
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
            if args.verbose:
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
        if args.verbose:
            print 'Received task %s (#%d)' % (jsondata['taskname'], jsondata['taskid'])

        taskdata['rootPath'] = CFG_GRADERQUEUE_ROOT
        if taskdata.has_key('restrictToPaths'):
            taskdata['restrictToPaths'] = map(lambda p: Template(p).safe_substitute(CFG_GRADERQUEUE_VARS), taskdata['restrictToPaths'])

        if args.debug:
            print ''
            print '* JSON sent to taskgrader:'
            print json.dumps(taskdata)
    
        # Send to taskgrader
        if args.debug:
            print ''
            print '* Output from taskgrader'
        proc = subprocess.Popen(['/usr/bin/python', CFG_TASKGRADER], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (procOut, procErr) = proc.communicate(input=json.dumps(taskdata))

        if args.debug:
            print ''
            print '* Results'

        # Read taskgrader output
        try:
            evalJson = json.loads(procOut)
        except:
            evalJson = None

        if evalJson:
            if args.verbose:
                print "Execution successful."
            if args.debug:
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
            if args.debug:
                print ''
                print '* Full report:'
                print json.dumps(evalJson)

            # Send back results
            resp = opener.open(CFG_GRADERQUEUE_SEND, data=urllib.urlencode(
                    {'taskid': jsondata['taskid'],
                     'resultdata': json.dumps({'errorcode': 0, 'taskdata': evalJson})})).read()

            if args.verbose:
                print "Sent results."
        else:
            if args.verbose:
                print "Taskgrader error."
            if args.debug:
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
            if args.verbose:
                print "Taskqueue response: (%d) %s" % (respjson['errorcode'], respjson['errormsg'])
        except:
            print "Error: Taskqueue answered results with invalid data (%s)" % resp
            sys.exit(1)

    print "No task available, sleeping."
