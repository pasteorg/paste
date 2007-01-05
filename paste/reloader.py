# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
A file monitor and server restarter.

Use this like:

..code-block:: Python

    import reloader
    reloader.install()

Then make sure your server is installed with a shell script like::

    err=3
    while test "$err" -eq 3 ; do
        python server.py
        err="$?"
    done

or is run from this .bat file (if you use Windows)::

    @echo off
    :repeat
        python server.py
    if %errorlevel% == 3 goto repeat

or run a monitoring process in Python (``paster serve --reload`` does
this).  Use the watch_file(filename) function to cause a
reload/restart for other other non-Python files (e.g., configuration
files).
"""

import os
import sys
import time
import threading
from paste.util.classinstance import classinstancemethod

def install(poll_interval=1):
    """
    Install the reloading monitor.

    On some platforms server threads may not terminate when the main
    thread does, causing ports to remain open/locked.  The
    ``raise_keyboard_interrupt`` option creates a unignorable signal
    which causes the whole application to shut-down (rudely).
    """
    mon = Monitor(poll_interval=poll_interval)
    t = threading.Thread(target=mon.periodic_reload)
    t.setDaemon(True)
    t.start()

class Monitor(object):

    instances = []
    global_extra_files = []

    def __init__(self, poll_interval):
        self.module_mtimes = {}
        self.keep_running = True
        self.poll_interval = poll_interval
        self.extra_files = self.global_extra_files[:]
        self.instances.append(self)

    def periodic_reload(self):
        while 1:
            if not self.check_reload():
                # use os._exit() here and not sys.exit() since within a
                # thread sys.exit() just closes the given thread and
                # won't kill the process; note os._exit does not call
                # any atexit callbacks, nor does it do finally blocks,
                # flush open files, etc.  In otherwords, it is rude.
                os._exit(3)
                break
            time.sleep(self.poll_interval)

    def check_reload(self):
        filenames = self.extra_files[:]
        for module in sys.modules.values():
            try:
                filenames.append(module.__file__)
            except AttributeError:
                continue
        for filename in filenames:
            try:
                stat = os.stat(filename)
                if stat:
                    mtime = stat.st_mtime
                else:
                    mtime = 0
            except (OSError, IOError):
                continue
            if filename.endswith('.pyc') and os.path.exists(filename[:-1]):
                mtime = max(os.stat(filename[:-1]).st_mtime, mtime)
            if not self.module_mtimes.has_key(filename):
                self.module_mtimes[filename] = mtime
            elif self.module_mtimes[filename] < mtime:
                print >> sys.stderr, (
                    "%s changed; reloading..." % filename)
                return False
        return True

    def watch_file(self, cls, filename):
        filename = os.path.abspath(filename)
        if self is None:
            for instance in cls.instances:
                instance.watch_file(filename)
            cls.global_extra_files.append(filename)
        else:
            self.extra_files.append(filename)

    watch_file = classinstancemethod(watch_file)

watch_file = Monitor.watch_file
