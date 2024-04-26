# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

"""
WSGI middleware

Captures any exceptions and prints a pretty report.
"""

from io import StringIO
import sys

from paste.util import converters, NO_DEFAULT
from paste.util.cgitb_hook import Hook


class CgitbMiddleware:

    def __init__(self, app,
                 global_conf=None,
                 display=NO_DEFAULT,
                 logdir=None,
                 context=5,
                 format="html"):
        self.app = app
        if global_conf is None:
            global_conf = {}
        if display is NO_DEFAULT:
            display = global_conf.get('debug')
        if isinstance(display, str):
            display = converters.asbool(display)
        self.display = display
        self.logdir = logdir
        self.context = int(context)
        self.format = format

    def __call__(self, environ, start_response):
        try:
            app_iter = self.app(environ, start_response)
            return self.catching_iter(app_iter, environ)
        except Exception:
            exc_info = sys.exc_info()
            start_response('500 Internal Server Error',
                           [('content-type', 'text/html')],
                           exc_info)
            response = self.exception_handler(exc_info, environ)
            response = response.encode('utf8')
            return [response]

    def catching_iter(self, app_iter, environ):
        if not app_iter:
            return
        error_on_close = False
        try:
            for v in app_iter:
                yield v
            if hasattr(app_iter, 'close'):
                error_on_close = True
                app_iter.close()
        except Exception:
            response = self.exception_handler(sys.exc_info(), environ)
            if not error_on_close and hasattr(app_iter, 'close'):
                try:
                    app_iter.close()
                except Exception:
                    close_response = self.exception_handler(
                        sys.exc_info(), environ)
                    response += (
                        '<hr noshade>Error in .close():<br>%s'
                        % close_response)
            response = response.encode('utf8')
            yield response

    def exception_handler(self, exc_info, environ):
        dummy_file = StringIO()
        hook = Hook(
            file=dummy_file,
            display=self.display,
            logdir=self.logdir,
            context=self.context,
            format=self.format)
        hook(*exc_info)
        return dummy_file.getvalue()


def make_cgitb_middleware(app, global_conf,
                          display=NO_DEFAULT,
                          logdir=None,
                          context=5,
                          format='html'):
    """
    Wraps the application in an error catcher based on the
    former ``cgitb`` module in the standard library.

      display:
        If true (or debug is set in the global configuration)
        then the traceback will be displayed in the browser

      logdir:
        Writes logs of all errors in that directory

      context:
        Number of lines of context to show around each line of
        source code
    """
    from paste.deploy.converters import asbool
    if display is not NO_DEFAULT:
        display = asbool(display)
    if 'debug' in global_conf:
        global_conf['debug'] = asbool(global_conf['debug'])
    return CgitbMiddleware(
        app, global_conf=global_conf,
        display=display,
        logdir=logdir,
        context=context,
        format=format)
