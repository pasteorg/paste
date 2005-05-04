import sys
import traceback
import cgi
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from paste.exceptions import formatter, collector, reporter
from paste import wsgilib

class ErrorMiddleware(object):

    def __init__(self, application, show_exceptions=True,
                 email_exceptions_to=[], smtp_server='localhost'):
        self.application = application
        self.show_exceptions = show_exceptions
        self.email_exceptions_to = email_exceptions_to
        self.smtp_server = smtp_server
    
    def __call__(self, environ, start_response):
        # We want to be careful about not sending headers twice,
        # and the content type that the app has committed to (if there
        # is an exception in the iterator body of the response)
        started = []

        def detect_start_response(status, headers):
            started.append(True)
            return start_response(status, headers)
        
        try:
            __traceback_supplement__ = Supplement, self, environ
            app_iter = self.application(environ, detect_start_response)
            return self.catching_iter(app_iter, environ)
        except:
            if not started:
                start_response('500 Internal Server Error',
                               [('content-type', 'text/html')])
            # @@: it would be nice to deal with bad content types here
            dummy_file = StringIO()
            response = self.exception_handler(sys.exc_info(), environ)
            return [response]

    def catching_iter(self, iter, environ):
        __traceback_supplement__ = Supplement, self, environ
        if not iter:
            raise StopIteration
        error_on_close = False
        try:
            for v in iter:
                yield v
            if hasattr(iter, 'close'):
                error_on_close = True
                iter.close()
        except:
            response = self.exception_handler(sys.exc_info(), environ)
            if not error_on_close and hasattr(iter, 'close'):
                try:
                    iter.close()
                except:
                    close_response = self.exception_handler(
                        sys.exc_info(), environ)
                    response += (
                        '<hr noshade>Error in .close():<br>%s'
                        % close_response)
            yield response

    def exception_handler(self, exc_info, environ):
        reported = False
        exc_data = collector.collect_exception(*exc_info)
        conf = environ.get('paste.config', {})
        extra_data = ''
        if conf.get('error_email'):
            rep = reporter.EmailReporter(
                to_addresses=conf['error_email'],
                from_address=conf.get('error_email_from', 'errors@localhost'),
                smtp_server=conf.get('smtp_server', 'localhost'),
                subject_prefix=conf.get('error_subject_prefix', ''))
            extra_data += self.send_report(rep, exc_data)
            reported = True
        if conf.get('error_log'):
            rep = reporter.LogReporter(
                filename=conf['error_log'])
            extra_data += self.send_report(rep, exc_data)
            # Well, this isn't really true, is it?
            reported = True
        if conf.get('show_exceptions_in_error_log', True):
            rep = reporter.FileReporter(
                file=environ['wsgi.errors'])
            extra_data += self.send_report(rep, exc_data)
            # Well, this isn't really true, is it?
            reported = True
        if conf.get('debug', False):
            html = self.error_template(
                formatter.format_html(exc_data), extra_data)
            reported = True
        else:
            html = self.error_template(
                '''
                An error occurred.  See the error logs for more information.
                (Turn debug on to display exception reports here)
                ''', '')
        if not reported:
            stderr = environ['wsgi.errors']
            err_report = formatter.format_text(exc_data, show_hidden_frames=True)
            err_report += '\n' + '-'*60 + '\n'
            stderr.write(err_report)
        return html

    def error_template(self, exception, extra):
        return '''
        <html>
        <head>
        <style type="text/css">%s</style>
        <title>Server Error</title>
        </head>
        <body>
        <h1>Server Error</h1>
        %s
        %s
        </body>
        </html>''' % (css, exception, extra)

    def send_report(self, reporter, exc_data):
        try:
            reporter.report(exc_data)
        except:
            output = StringIO()
            traceback.print_exc(file=output)
            return """
            <p>Additionally an error occurred while sending the %s report:

            <pre>%s</pre>
            </p>""" % (
                cgi.escape(str(reporter)), output.getvalue())
        else:
            return ''

class Supplement(object):
    def __init__(self, middleware, environ):
        self.middleware = middleware
        self.environ = environ
        self.source_url = wsgilib.construct_url(environ)
    def extraData(self):
        data = {}
        cgi_vars = data[('extra', 'CGI Variables')] = {}
        wsgi_vars = data[('extra', 'WSGI Variables')] = {}
        hide_vars = ['paste.config', 'wsgi.errors', 'wsgi.input']
        for name, value in self.environ.items():
            if name.upper() == name:
                cgi_vars[name] = value
            elif name not in hide_vars:
                wsgi_vars[name] = value
        data[('extra', 'Configuration')] = dict(self.environ['paste.config'])
        return data

css = """
table {
  width: 100%;
}

tr.header {
  background-color: #006;
  color: #fff;
}

tr.even {
  background-color: #ddd;
}

table.variables td {
  verticle-align: top;
  overflow: auto;
}

a.button {
  background-color: #ccc;
  border: 2px outset #aaa;
  color: #000;
  text-decoration: none;
}

a.button:hover {
  background-color: #ddd;
}
"""
    
