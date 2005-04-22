"""
WSGI middleware

Wraps a Python CGI script.  Can handle multi-threading for basic CGI
scripts.  May effect other parts of the system that use the cgi module
(though it attempts not to).  Doesn't handle other kinds of CGI
scripts, which would actually require spawning a separate process.
"""
# @@: still untested

import cgi
import sys
try:
    import threading
    import thread
except ImportError:
    threading = None
threadedprint = None
from cStringIO import StringIO
import os
import rfc822
import imp
from UserDict import DictMixin

_cgi_hook_installed = False
_stdout_hook_installed = False
_environs = {}
_real_environ = os.environ

class CGIWrapper(object):

    if threading:
        threading_lock = threading.Lock()

    def __init__(self, cgi_filename):
        self.cgi_filename = cgi_filename

    def __call__(self, environ, start_response):
        if environ['wsgi.multithread']:
            output = self.threaded_std(environ['wsgi.input'])
        else:
            output = self.non_threaded_std(environ['wsgi.input'])
        self.install_cgi_hook()
        name = contextName()
        try:
            _environs[name] = environ
            self.run_script()
        finally:
            if _environs.has_key(name):
                del _environs[name]
            if environ['wsgi.multithread']:
                self.remove_threaded_std()
            else:
                self.remove_non_threaded_std()
        parseable = StringIO(output.getvalue())
        message = rfc822.Message(parseable)
        body = parseable.read()
        #sys.__stdout__.write('Content-type: text/html\n')
        #sys.__stdout__.flush()
        
        #sys.__stdout__.write(str(message) + body)
        #sys.__stdout__.flush()
        status = message.getheader('status', None)
        if status is None:
            status = '200 OK'
        else:
            del message['status']
        headers = message.items()
        writer = start_response(status, headers)
        return [body]

    suffix_info = [t for t in imp.get_suffixes() if t[0] == '.py'][0]

    def run_script(self):
        f = open(self.cgi_filename, self.suffix_info[1])
        try:
            mod = imp.load_module('__main__', f, self.cgi_filename,
                                  self.suffix_info)
        except SystemExit:
            pass
        f.close()

    def threaded_std(self, input):
        self.install_threading()
        output = StringIO()
        threadedprint.register(output)
        threadedprint.registerInput(input)

    def remove_threaded_std(self):
        threadedprint.deregister()

    def non_threaded_std(self, input):
        output = StringIO()
        sys.stdout = output
        sys.stdin = input
        return output

    def remove_non_threaded_std(self):
        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__
    
    def install_threading(self):
        global threadedprint, _stdout_hook_installed
        """
        Installs an alternate version of sys.stdout
        """
        if _stdout_hook_installed:
            return
        self.threading_lock.acquire()
        try:
            if _stdout_hook_installed:
                return
            from util import threadedprint
            threadedprint.install(
                default=sys.stdout)
            _stdout_hook_installed = True
        finally:
            self.threading_lock.release()
            
    def install_cgi_hook(self):
        global _cgi_hook_installed
        if _cgi_hook_installed:
            return
        if threading:
            self.threading_lock.acquire()
        try:
            if _cgi_hook_installed:
                return
            cgi.FieldStorage = FieldStorageWrapper
            os.environ = EnvironWrapper()
            _cgi_hook_installed = True
        finally:
            if threading:
                self.threading_lock.release()

def contextName():
    if not threading:
        return None
    else:
        return thread.get_ident()

_real_FieldStorage = cgi.FieldStorage

class FieldStorageWrapper(_real_FieldStorage):

    def __init__(self, fp=None, headers=None, outerboundary="",
                 environ=os.environ, keep_blank_values=0, strict_parsing=0):
        if fp is None:
            # @@: Should I look for sys.stdin too?
            # Or should I be replacing sys.stdin entirely?
            fp = _environs[contextName()]['wsgi.input']
        if environ is os.environ:
            environ = _environs[contextName()]
        _real_FieldStorage.__init__(
            self,
            fp=fp, headers=headers,
            outerboundary=outerboundary, environ=environ,
            keep_blank_values=keep_blank_values,
            strict_parsing=strict_parsing)

class EnvironWrapper(DictMixin):

    def __getitem__(self, key):
        try:
            d = _environs[contextName()]
        except KeyError:
            return _real_environ[key]
        else:
            return d[key]

    def keys(self):
        try:
            return _environs[contextName()].keys()
        except KeyError:
            return _real_environ.keys()

    def copy(self):
        try:
            return _environs[contextName()].copy()
        except KeyError:
            return _real_environ.copy()

