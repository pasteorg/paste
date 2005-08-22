import sys
from cStringIO import StringIO
import re
import cgi
from paste.util import threadedprint
from paste import wsgilib

_threadedprint_installed = False

__all__ = ['PrintDebugMiddleware']

class TeeFile(object):

    def __init__(self, *files):
        self.files = files

    def write(self, v):
        for file in self.files:
            file.write(v)

class PrintDebugMiddleware(object):

    """
    This middleware captures all the printed statements, and inlines
    them in HTML pages, so that you can see all the (debug-intended)
    print statements in the page itself.  Install like::

        important_middleware.append(
            'paste.printdebug.PrintDebugMiddleware')

    In your configuration file.
    """

    log_template = (
        '<pre style="width: 40%%; border: 2px solid #000; white-space: normal; '
        'background-color: #ffd; color: #000; float: right;">'
        '<b style="border-bottom: 1px solid #000">Log messages</b><br>'
        '%s</pre>')

    def __init__(self, app, global_conf=None, force_content_type=False):
        self.app = app
        self.force_content_type = force_content_type

    def __call__(self, environ, start_response):
        global _threadedprint_installed
        if not _threadedprint_installed:
            # @@: Not strictly threadsafe
            _threadedprint_installed = True
            threadedprint.install(leave_stdout=True)
        logged = StringIO()
        if environ['paste.config'].get('printdebug_print_error'):
            replacement_stdout = TeeFile(environ['wsgi.errors'], logged)
            environ['paste.config']['show_exceptions_in_error_log'] = False
        else:
            replacement_stdout = logged
        output = StringIO()
        try:
            threadedprint.register(replacement_stdout)
            status, headers, body = wsgilib.capture_output(
                environ, start_response, self.app)
            if status is None:
                # Some error occurred
                status = '500 Server Error'
                headers = [('Content-type', 'text/html')]
                start_response(status, headers)
                if not body:
                    body = 'An error occurred'
            content_type = wsgilib.header_value(headers, 'content-type')
            if (not self.force_content_type and
                (not content_type
                 or not content_type.startswith('text/html'))):
                if replacement_stdout == logged:
                    # Then the prints will be lost, unless...
                    environ['wsgi.errors'].write(logged.getvalue())
                return [body]
            body = self.add_log(body, logged.getvalue())
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
