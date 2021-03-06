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
parser.add_argument('-l', dest='limit', type=int, default=200, help='limit to this many records')
args = parser.parse_args(sys.argv[1:])

DATETIME  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
TIMESTAMP = int(time.time())

if args.whoami is None:
    args.whoami = getpass.getuser() # username
ROOT = "/data/data/org.mozilla.fennec_%s" % args.whoami
if args.verbose:
    print >> sys.stderr, "Using root directory '%s'" % (ROOT)

OUTPUT_DIR = "/sdcard"
TEMP_DIR   = "/tmp"
ADB        = "adb"
SQLITE     = "sqlite3"

TABLES = [
    ("files/mozilla/%(PROFILE)s", "browser.db", "history"), # too much?
    ("files/mozilla/%(PROFILE)s", "browser.db", "bookmarks"),
    # ("files/mozilla/%(PROFILE)s", "browser.db", "tree"),
    ("files/mozilla/%(PROFILE)s", "tabs.db", "tabs"),
    ("files/mozilla/%(PROFILE)s", "tabs.db", "clients"),
    ("files/mozilla/%(PROFILE)s", "signons.sqlite", "moz_deleted_logins"),
    ("files/mozilla/%(PROFILE)s", "signons.sqlite", "moz_logins"),
    # ("files/mozilla/%(PROFILE)s", "permissions.db", "permissions"),
    ("files/mozilla/%(PROFILE)s", "formhistory.sqlite", "moz_deleted_formhistory"),
    ("files/mozilla/%(PROFILE)s", "formhistory.sqlite", "moz_formhistory"),
    ("databases", "clients_database", "clients"),
    ("databases", "clients_database", "commands"),
    ("databases", "history_extension_database", "HistoryExtension"), ]

if args.db and args.table:
    TABLES = [ (d, args.db, args.table) ]
elif args.db:
    args.db = args.db.lower()
    TABLES = [ (d, k, v) for (d, k, v) in TABLES if args.db in k.lower() ] # filter
elif args.table:
    args.table = args.table.lower()
    TABLES = [ (d, k, v) for (d, k, v) in TABLES if args.table in v.lower() ] # filter

HTML_HEADER = """<html>
<head>
<title>dumpdbs at %s (%s)</title>
<style>
table {
  border-collapse: collapse;
}
td, th {
  border: 1px solid LightGray;
}
</style>
</head>
<body>
<h1>dumpdbs at %s (%s)</h1>
""" % (DATETIME, TIMESTAMP, DATETIME, TIMESTAMP)
HTML_FOOTER = """</body>
</html>"""

HTML_TABLE_HEADER = """<table>"""
HTML_TABLE_FOOTER = """</table>"""

output = subprocess.check_output([ADB, 'shell', 'run-as org.mozilla.fennec_%s ls %s/files/mozilla' % (args.whoami, ROOT)])

MANGLED_PROFILE = None
for line in output.split():
    line = line.strip()
    if not line:
        continue
    if not args.profile in line:
        continue
    MANGLED_PROFILE = line

if not MANGLED_PROFILE:
    print >> sys.stderr, "Couldn't find profile '%s'" % args.profile
    exit(1)
else:
    if args.verbose:
        print >> sys.stderr, "Found profile '%s'" % (MANGLED_PROFILE)

subst_dict = { "PROFILE": MANGLED_PROFILE };
FILES_TO_COPY = set([ (d % subst_dict, k) for d, k, _ in TABLES ])
NUM_FILES_TO_COPY = len(FILES_TO_COPY)
COPIED = {}

if args.verbose:
    print >> sys.stderr, "Copying %s files..." % NUM_FILES_TO_COPY
for DIR, FILE in FILES_TO_COPY:
    I = "%s/%s/%s" % (ROOT, DIR, FILE)             # file on device, not pull-able
    O = "%s/%s-%s" % (OUTPUT_DIR, FILE, TIMESTAMP) # file on device, pull-able
    L = "%s/%s-%s" % (TEMP_DIR, FILE, TIMESTAMP)   # file in temp storage on desktop
    try:
        print >> sys.stderr, subprocess.check_output([ADB, "shell", "run-as org.mozilla.fennec_%s dd if=%s of=%s" % (args.whoami, I, O)]) # move it to pull-able
        print >> sys.stderr, subprocess.check_output([ADB, "pull", O, L]) # pull it
    except:
        if args.verbose:
            print >> sys.stderr, "Couldn't dd and pull %s" % FILE
        continue

    COPIED[FILE] = True
    try:
        print >> sys.stderr, subprocess.check_output([ADB, "shell", "run-as org.mozilla.fennec_%s rm %s" % (args.whoami, O)]) # delete pull-able file
    except:
        if args.verbose:
            print >> sys.stderr, "Couldn't rm %s" % O
        continue

if args.verbose:
    print >> sys.stderr, "Copying %s files... DONE" % NUM_FILES_TO_COPY
    print >> sys.stderr, "Copied %s of %s files." % (len(COPIED), NUM_FILES_TO_COPY)

print HTML_HEADER

for (directory, db, table) in TABLES:
    if not COPIED.has_key(db):
        continue

    if (table == "tree"):
        SQL = "select _id, guid, parent, position, title from bookmarks order by _id;"
        try:
            output = subprocess.check_output([SQLITE, "-csv", L, SQL])
        except:
            if args.verbose:
                print >> sys.stderr, "Couldn't %s in db %s" % (table, db)
            continue

        class Node:
            def __init__(self, _id, guid, parent, position, title, children=None):
                self._id = _id
                self.guid = guid
                self.parent = parent
                self.position = position
                self.title = title
                if children is None:
                    children = []
                self.children = children

            def __repr__(self):
                return "Node<%s,%s,%s,%s,%s,\n%s>" % (self._id, self.guid, self.parent, self.position, self.title, self.children)

            def html(self, verbose=False):
                print "<ul>"
                print "<b>%s</b>" % self.title,
                if verbose:
                    print " androidID=%s guid=%s parentAndroidID=%s position=%s" % (self._id, self.guid, self.parent, self.position)
                for child in self.children:
                    child.html(verbose)
                print "</ul>"

        tree = {}
        for rec in output.split("\n"):
            if (not rec):
                continue
            _id, guid, parent, position, title = rec.split(",")
            _id = int(_id)
            if (_id == 0):
                continue
            parent = int(parent)
            position = int(position)
            children = []
            x = Node(_id, guid, parent, position, title)
            if (not tree.has_key(parent)):
                tree[parent] = []
            tree[parent].append(x)

        root = Node(0, "places", 0, 0, "places", tree[0])
        cs = [root]
        while cs:
            c = cs.pop()
            if tree.has_key(c._id):
                c.children = sorted(tree[c._id], key=lambda x: x.position)
            else:
                c.children = []
            cs = cs + c.children

        print "<div>"
        print "<h2>%s</h2>" % SQL
        root.html(args.verbose)
        print "</div>"
        continue

    SQL = "select * from %s limit %s;" % (table, args.limit)
    L = "%s/%s-%s" % (TEMP_DIR, db, TIMESTAMP)   # file in temp storage on desktop
    try:
        output = subprocess.check_output([SQLITE, "-html", "-header", L, SQL])
    except:
        if args.verbose:
            print >> sys.stderr, "Couldn't select * from %s in db %s" % (table, db)
        continue

    print "<div>"
    print "<h2>%s: %s</h2>" % (db, SQL)
    print HTML_TABLE_HEADER
    print output
    print HTML_TABLE_FOOTER
    print "</div>"

print HTML_FOOTER

local_files = []
for db in COPIED.keys():
    L = "%s/%s-%s" % (TEMP_DIR, db, TIMESTAMP)   # file in temp storage on desktop
    local_files.append(L)

for L in local_files:
    if not args.keep_db_files:
        # either delete...
        try:
            os.remove(L)
        except OSError:
            if args.verbose:
                print >> sys.stderr, "Couldn't remove %s" % L
    else:
        # or make sure it ends with '.sqlite'
        if not 'sqlite' in L:
            try:
                os.rename(L, L + '.sqlite')
                L = L + '.sqlite'
            except OSError:
                if args.verbose:
                    print >> sys.stderr, "Couldn't rename %s" % L
        if args.verbose:
            print >> sys.stderr, "Kept database file %s" % L
