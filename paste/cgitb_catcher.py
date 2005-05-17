"""
WSGI middleware

Captures any exceptions and prints a pretty report.  See the cgitb
documentation for more:
  http://python.org/doc/current/lib/module-cgitb.html
"""

import cgitb
from cStringIO import StringIO
import sys

class DummyFile(object):
    pass

def middleware(application, **kw):

    def start_application(environ, start_response):
        started = []

        def detect_start_response(status, headers, exc_info=None):
            started.append(start_response(status, headers, exc_info))
            return started[0]
        
        try:
            app_iter = application(environ, detect_start_response)
            return catching_iter(app_iter)
        except:
            if not started:
                write = start_response('500 Internal Server Error',
                                       [('content-type', 'text/html')])
            else:
                write = started[0]
            dummy_file = DummyFile()
            dummy_file.write = write
            dummy_file = StringIO()
            hook = cgitb.Hook(**kw)
            hook.file = dummy_file
            hook(*sys.exc_info())
            return [dummy_file.getvalue()]

    def catching_iter(app_iter):
        if not app_iter:
            raise StopIteration
        try:
            for v in app_iter:
                yield v
        except:
            exc = sys.exc_info()
            dummy_file = StringIO()
            hook = cgitb.Hook(**kw)
            hook.file = dummy_file
            hook(*exc)
            yield dummy_file.getvalue()

    return start_application
