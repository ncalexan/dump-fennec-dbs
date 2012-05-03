#!/usr/bin/python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import sys
import datetime
import time
import subprocess
import getpass
import os

# parse command line arguments
parser = argparse.ArgumentParser(description='Pull and dump Fennec databases from devices.')
parser.add_argument('-v', dest='verbose', action='store_true', default=False, help='verbose output')
parser.add_argument('-P', dest='profile', default='default', help='profile')
parser.add_argument('-w', dest='whoami', default=None, help='run-as org.mozilla.fennec_${WHOAMI} (default \'username\')')
parser.add_argument('-d', dest='db',    default=None, help='database to dump')
parser.add_argument('-t', dest='table', default=None, help='table to dump')
parser.add_argument('-k', dest='keep_db_files', action='store_true', default=False, help='keep database files in temp')
args = parser.parse_args(sys.argv[1:])

DATETIME  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
TIMESTAMP = int(time.time())

if args.whoami is None:
    args.whoami = getpass.getuser() # username
ROOT = "/data/data/org.mozilla.fennec_%s/shared_prefs" % args.whoami
if args.verbose:
    print >> sys.stderr, "Using root directory '%s'" % (ROOT)

ADB = "adb"

output = subprocess.check_output([ADB, 'shell', 'run-as org.mozilla.fennec_%s ls %s' % (args.whoami, ROOT)])

for line in output.split('\n'):
    line = line.strip()
    if not line:
        continue
    if not line.endswith('.xml'):
        continue

    cat = subprocess.check_output([ADB, 'shell', 'run-as org.mozilla.fennec_%s cat %s/%s' % (args.whoami, ROOT, line)])
    print "FILE: %s" % line
    for catline in cat.split('\n'):
        print "   ", catline
