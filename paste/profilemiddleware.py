import sys
import hotshot
import hotshot.stats
import threading
import cgi
from cStringIO import StringIO
from paste import wsgilib

class ProfileMiddleware(object):

    style = ('background-color: #ff9; color: #000; '
             'border: 2px solid #000; padding: 5px;')

    def __init__(self, application):
        self.application = application
        self.lock = threading.Lock()

    def __call__(self, environ, start_response):
        prof_filename = environ['paste.config'].get(
            'hotshot_log', 'profile.log')
        display_limit = environ['paste.config'].get('hotshot_limit', 40)
        response = []
        body = []
        def replace_start_response(status, headers):
            response.extend([status, headers])
            start_response(status, headers)
            return body.append
        def run_app():
            body.extend(self.application(environ, replace_start_response))
        self.lock.acquire()
        try:
            prof = hotshot.Profile(prof_filename)
            prof.addinfo('URL', environ.get('PATH_INFO', ''))
            try:
                prof.runcall(run_app)
            finally:
                prof.close()
            body = ''.join(body)
            headers = response[1]
            content_type = wsgilib.header_value(headers, 'content-type')
            if not content_type.startswith('text/html'):
                # We can't add info to non-HTML output
                return [body]
            stats = hotshot.stats.load(prof_filename)
            stats.strip_dirs()
            stats.sort_stats('time', 'calls')
            output = capture_output(stats.print_stats, display_limit)
            output_callers = capture_output(
                stats.print_callers, display_limit)
            body += '<pre style="%s">%s\n%s</pre>' % (
                self.style, cgi.escape(output), cgi.escape(output_callers))
            return [body]
        finally:
            self.lock.release()

def capture_output(func, *args, **kw):
    # Not threadsafe!
    out = StringIO()
    old_stdout = sys.stdout
    sys.stdout = out
    try:
        func(*args, **kw)
    finally:
        sys.stdout = old_stdout
    return out.getvalue()
