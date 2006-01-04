# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Middleware that displays everything that is printed inline in
application pages.
"""

from cStringIO import StringIO
import re
import cgi
from paste.util import threadedprint
from paste import wsgilib
from paste import response
from paste.deploy.converters import asbool

_threadedprint_installed = False

__all__ = ['PrintDebugMiddleware']

class TeeFile(object):

    def __init__(self, *files):
        self.files = files

    def write(self, v):
        if isinstance(v, unicode):
            # WSGI is picky in this case
            v = str(v)
        for file in self.files:
            file.write(v)

class PrintDebugMiddleware(object):

    """
    This middleware captures all the printed statements, and inlines
    them in HTML pages, so that you can see all the (debug-intended)
    print statements in the page itself.
    """

    log_template = (
        '<pre style="width: 40%%; border: 2px solid #000; white-space: normal; '
        'background-color: #ffd; color: #000; float: right;">'
        '<b style="border-bottom: 1px solid #000">Log messages</b><br>'
        '%s</pre>')

    def __init__(self, app, global_conf=None, force_content_type=False,
                 print_wsgi_errors=True):
        self.app = app
        self.force_content_type = force_content_type
        self.print_wsgi_errors = asbool(print_wsgi_errors)

    def __call__(self, environ, start_response):
        global _threadedprint_installed
        if environ.get('paste.testing'):
            # In a testing environment this interception isn't
            # useful:
            return self.app(environ, start_response)
        if not _threadedprint_installed:
            # @@: Not strictly threadsafe
            _threadedprint_installed = True
            threadedprint.install(leave_stdout=True)
        logged = StringIO()
        if self.print_wsgi_errors:
            replacement_stdout = TeeFile(environ['wsgi.errors'], logged)
        else:
            replacement_stdout = logged
        output = StringIO()
        try:
            threadedprint.register(replacement_stdout)
            status, headers, body = wsgilib.intercept_output(
                environ, self.app)
            if status is None:
                # Some error occurred
                status = '500 Server Error'
                headers = [('Content-type', 'text/html')]
                start_response(status, headers)
                if not body:
                    body = 'An error occurred'
            content_type = response.header_value(headers, 'content-type')
            if (not self.force_content_type and
                (not content_type
                 or not content_type.startswith('text/html'))):
                if replacement_stdout == logged:
                    # Then the prints will be lost, unless...
                    environ['wsgi.errors'].write(logged.getvalue())
                start_response(status, headers)
                return [body]
            response.remove_header(headers, 'content-length')
            body = self.add_log(body, logged.getvalue())
            start_response(status, headers)
            return [body]
        finally:
            threadedprint.deregister()

    _body_re = re.compile(r'<body[^>]*>', re.I)
        
    def add_log(self, html, log):
        if not log:
            return html
        text = cgi.escape(log)
        text = text.replace('\n', '<br>\n')
        text = text.replace('  ', '&nbsp; ')
        log = self.log_template % text
        match = self._body_re.search(html)
        if not match:
            return log + html
        else:
            return html[:match.end()] + log + html[match.end():]
