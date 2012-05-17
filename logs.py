#!/usr/bin/python

# Read adb logcat -v time output from stdin and write Android Sync logs to text files.
# use like:
# $ adb logcat -c && adb logcat -v time | logs.py -d /Users/ncalexan/Mozilla/logs

import sys
import time
import os
import argparse

DEFAULT_BEG_SENTINEL = "Got onPerformSync. Extras bundle is"
DEFAULT_END_SENTINEL = "Setting minimum next sync time to"

# parse command line arguments
parser = argparse.ArgumentParser(description='Read adb logcat -v time output from stdin and write Android Sync logs to text files.')
parser.add_argument('-d', dest='directory', default='.', help='directory to write log files to')
parser.add_argument('-p', dest='prefix', default='FxSync', help='text files will be named PREFIX-TIMESTAMP.txt')
parser.add_argument('-b', dest='beg_sentinel', default=DEFAULT_BEG_SENTINEL, help='text sentinel to begin logging')
parser.add_argument('-e', dest='end_sentinel', default=DEFAULT_END_SENTINEL, help='text sentinel to end logging')
args = parser.parse_args(sys.argv[1:])

# I SyncAdapter(14434)          Got onPerformSync. Extras bundle is Bundle[{ignore_backoff=true, ignore_settings=true, force=true}]
# I SyncAdapter(14434)          Setting minimum next sync time to 1337191588829

LOG = None

def get_timestamp(line):
    """Extract a timestamp from a text line formatted by `adb logcat -v time`, like:
05-16 11:18:46.355 D/AlarmManager(  207): Added alarm Alarm{41533d50 type 2 com.google.android.gsf} type:ELAPSED_REALTIME_WAKEUP when: After 0h:4m:59.0s
"""
    timestamp = 1000 * int(time.time())
    try:
        linestamp = line.split(' I/')[0]
        linestamp, millis = linestamp.split('.')
        linestamp = str(time.localtime().tm_year) + "-" + linestamp
        timestamp = int(time.mktime(time.strptime(linestamp, "%Y-%m-%d %H:%M:%S")))
        timestamp = 1000 * timestamp + int(millis)
    except:
        pass
    return timestamp

def log_filename(line):
    """Return a suitable filename for a log starting with given line."""
    return '%s/%s-%s.txt' % (args.directory, args.prefix, get_timestamp(line))

# don't buffer output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

while 1:
    try:
        line = sys.stdin.readline()
    except KeyboardInterrupt:
        break

    if not line:
        break

    if args.beg_sentinel in line:
        filename = log_filename(line)
        print "Logging to file %s ..." % filename,
        if os.path.exists(filename):
            print "skipped."
        else:
            LOG = open(filename, 'w')

    if LOG:
        LOG.write(line)

    if args.end_sentinel in line:
        if LOG:
            LOG.close()
            LOG = None
            print "done."
