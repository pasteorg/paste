"""
Middleware that checks HTML and appends messages about the validity of
the HTML.  Uses: http://www.htmlhelp.com/tools/validator/ -- interacts
with the command line client.  Use the configuration ``wdg_path`` to
override the path (default: looks for ``validate`` in $PATH).

To install, in your web context's __init__.py::

    def urlparser_wrap(environ, start_response, app):
        return wdg_validate.WDGValidateMiddleware(app)(
            environ, start_response)
"""

from cStringIO import StringIO
import subprocess
from paste import wsgilib
import re
import cgi

class WDGValidateMiddleware(object):

    _end_body_regex = re.compile(r'</body>', re.I)

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        output = StringIO()
        response = []
        def writer_start_response(status, headers, exc_info=None):
            response.extend((status, headers))
            start_response(status, headers, exc_info)
            return output.write
        app_iter = self.app(environ, writer_start_response)
        try:
            for s in app_iter:
                output.write(s)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()
        page = output.getvalue()
        status, headers = response
        v = wsgilib.header_value(headers, 'content-type')
        if (not v.startswith('text/html')
            and not v.startswith('text/xhtml+xml')):
            # Can't validate
            # @@: Should validate CSS too... but using what?
            return [page]
        ops = []
        if v.startswith('text/xhtml+xml'):
            ops.append('--xml')
        # @@: Should capture encoding too
        conf = environ['paste.config']
        wdg_path = conf.get('wdg_path', 'validate')
        proc = subprocess.Popen([wdg_path] + ops,
                                shell=False,
                                close_fds=True,
                                stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        stdout = proc.communicate(page)[0]
        proc.wait()
        if not stdout:
            return [page]
        add_text = '<pre style="background-color: #ffd; color: #600; border: 1px solid #000;">%s</pre>' % cgi.escape(stdout)
        match = self._end_body_regex.search(page)
        if match:
            page = page[:match.start()] + add_text + page[match.end():]
        else:
            page += add_text
        return [page]
    
                                
            
        
