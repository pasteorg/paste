"""
Error handler middleware, and paste.config reporter integration

Usage::

    error_caching_wsgi_app = ErrorMiddleware(wsgi_app)

These configuration keys are used:

``debug``:
    show the errors in the browser
``error_email``:
    if present, send errors to this email address
``error_log``:
    if present, write errors to this file
``show_exceptions_in_error_log``:
    if true (the default) then write errors to wsgi.errors

You can also use this outside of a web context, like::

    import sys
    import paste
    import paste.error_middleware
    try:
        do stuff
    except:
        paste.error_middleware.exception_handler(
            sys.exc_info(), paste.CONFIG, sys.stderr, html=False)

If you want to report, but not fully catch the exception, call
``raise`` after ``exception_handler``, which (when given no argument)
will reraise the exception.

By setting 'paste.throw_errors' to a true value, this middleware is
disabled.  This can be useful in a testing environment where you don't
want errors to be caught and transformed.
"""

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

    def __init__(self, application):
        self.application = application
    
    def __call__(self, environ, start_response):
        # We want to be careful about not sending headers twice,
        # and the content type that the app has committed to (if there
        # is an exception in the iterator body of the response)
        started = []
        if environ.get('paste.throw_errors'):
            return self.application(environ, start_response)
        environ['paste.throw_errors'] = True

        def detect_start_response(status, headers, exc_info=None):
            started.append(True)
            return start_response(status, headers, exc_info)
        
        try:
            __traceback_supplement__ = Supplement, self, environ
            app_iter = self.application(environ, detect_start_response)
            return self.catching_iter(app_iter, environ)
        except:
            if not started:
                start_response('500 Internal Server Error',
                               [('content-type', 'text/html')])
            # @@: it would be nice to deal with bad content types here
            response = self.exception_handler(sys.exc_info(), environ)
            return [response]

    def catching_iter(self, app_iter, environ):
        __traceback_supplement__ = Supplement, self, environ
        if not app_iter:
            raise StopIteration
        error_on_close = False
        try:
            for v in app_iter:
                yield v
            if hasattr(app_iter, 'close'):
                error_on_close = True
                app_iter.close()
        except:
            response = self.exception_handler(sys.exc_info(), environ)
            if not error_on_close and hasattr(app_iter, 'close'):
                try:
                    app_iter.close()
                except:
                    close_response = self.exception_handler(
                        sys.exc_info(), environ)
                    response += (
                        '<hr noshade>Error in .close():<br>%s'
                        % close_response)
            yield response

    def exception_handler(self, exc_info, environ):
        return handle_exception(
            exc_info, environ['paste.config'], environ['wsgi.errors'],
            html=True)

class Supplement(object):
    def __init__(self, middleware, environ):
        self.middleware = middleware
        self.environ = environ
        self.source_url = wsgilib.construct_url(environ)
    def extraData(self):
        data = {}
        cgi_vars = data[('extra', 'CGI Variables')] = {}
        wsgi_vars = data[('extra', 'WSGI Variables')] = {}
        hide_vars = ['paste.config', 'wsgi.errors', 'wsgi.input',
                     'wsgi.multithread', 'wsgi.multiprocess',
                     'wsgi.run_once', 'wsgi.version',
                     'wsgi.url_scheme']
        for name, value in self.environ.items():
            if name.upper() == name:
                if value:
                    cgi_vars[name] = value
            elif name not in hide_vars:
                wsgi_vars[name] = value
        if self.environ['wsgi.version'] != (1, 0):
            wsgi_vars['wsgi.version'] = self.environ['wsgi.version']
        proc_desc = tuple([int(bool(self.environ[key]))
                           for key in ('wsgi.multiprocess',
                                       'wsgi.multithread',
                                       'wsgi.run_once')])
        wsgi_vars['wsgi process'] = self.process_combos[proc_desc]
        data[('extra', 'Configuration')] = dict(self.environ['paste.config'])
        return data

    process_combos = {
        # multiprocess, multithread, run_once
        (0, 0, 0): 'Non-concurrent server',
        (0, 1, 0): 'Multithreaded',
        (1, 0, 0): 'Multiprocess',
        (1, 1, 0): 'Multi process AND threads (?)',
        (0, 0, 1): 'Non-concurrent CGI',
        (0, 1, 1): 'Multithread CGI (?)',
        (1, 0, 1): 'CGI',
        (1, 1, 1): 'Multi thread/process CGI (?)',
        }
    
def handle_exception(exc_info, conf, error_stream, html=True):
    reported = False
    exc_data = collector.collect_exception(*exc_info)
    extra_data = ''
    if conf.get('error_email'):
        rep = reporter.EmailReporter(
            to_addresses=conf['error_email'],
            from_address=conf.get('error_email_from', 'errors@localhost'),
            smtp_server=conf.get('smtp_server', 'localhost'),
            subject_prefix=conf.get('error_subject_prefix', ''))
        rep_err = send_report(rep, exc_data, html=html)
        if not rep_err:
            extra_data += rep_err
            reported = True
    if conf.get('error_log'):
        rep = reporter.LogReporter(
            filename=conf['error_log'])
        rep_err = send_report(rep, exc_data, html=html)
        if not rep_err:
            extra_data += rep_err
            reported = True
    if conf.get('show_exceptions_in_error_log', True):
        rep = reporter.FileReporter(
            file=error_stream)
        rep_err = send_report(rep, exc_data, html=html)
        if not rep_err:
            extra_data += rep_err
            reported = True
    else:
        error_stream.write('Error - %s: %s\n' % (
            exc_data.exception_type, exc_data.exception_value))
    if html:
        if conf.get('debug', False):
            return_error = error_template(
                formatter.format_html(exc_data), extra_data)
            extra_data = ''
            reported = True
        else:
            return_error = error_template(
            '''
            An error occurred.  See the error logs for more information.
            (Turn debug on to display exception reports here)
            ''', '')
    else:
        return_error = None
    if not reported and error_stream:
        err_report = formatter.format_text(exc_data, show_hidden_frames=True)
        err_report += '\n' + '-'*60 + '\n'
        error_stream.write(err_report)
    if extra_data:
        error_stream.write(extra_data)
    return return_error

def send_report(rep, exc_data, html=True):
    try:
        rep.report(exc_data)
    except:
        output = StringIO()
        traceback.print_exc(file=output)
        if html:
            return """
            <p>Additionally an error occurred while sending the %s report:

            <pre>%s</pre>
            </p>""" % (
                cgi.escape(str(rep)), output.getvalue())
        else:
            return (
                "Additionally an error occurred while sending the "
                "%s report:\n%s" % (str(rep), output.getvalue()))
    else:
        return ''

def error_template(exception, extra):
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
