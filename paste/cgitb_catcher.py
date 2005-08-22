"""
WSGI middleware

Captures any exceptions and prints a pretty report.  See the cgitb
documentation for more:
  http://python.org/doc/current/lib/module-cgitb.html
"""

import cgitb
from cStringIO import StringIO
import sys
from paste.deploy import converters

class NoDefault:
    pass

class CgitbMiddleware(object):

    def __init__(self, app,
                 global_conf,
                 display=NoDefault,
                 logdir=None,
                 context=5,
                 format="html"):
        self.app = application
        if display is NoDefault:
            display = global_conf.get('debug')
        self.display = converters.asbool(display)
        self.logdir = logdir
        self.context = int(context)
        self.format = format

    def __call__(self, environ, start_response):
        try:
            app_iter = self.app(environ, start_response)
            return catching_iter(app_iter)
        except:
            exc_info = sys.exc_info()
            start_response('500 Internal Server Error',
                           [('content-type', 'text/html')],
                           exc_info)
            dummy_file = StringIO()
            hook = cgitb.Hook(file=dummy_file,
                              display=self.display,
                              logdir=self.logdir,
                              context=self.context,
                              format=self.format)
            hook(*exc_info)
            return [dummy_file.getvalue()]

    def catching_iter(self, app_iter):
        if not app_iter:
            raise StopIteration
        try:
            for v in app_iter:
                yield v
        except:
            exc_info = sys.exc_info()
            dummy_file = StringIO()
            hook = cgitb.Hook(file=dummy_file,
                              display=self.display,
                              logdir=self.logdir,
                              context=self.context,
                              format=self.format)
            hook(*exc_info)
            yield dummy_file.getvalue()
