import sys
import threading
from paste.exceptions import errormiddleware, formatter, collector

class EvalException(object):

    def __init__(self, application, global_conf=None):
        self.application = application
        self.debugging = False
        # This is a single-threaded middleware:
        self.lock = threading.Lock()
        self.exc_info = None

    def __call__(self, environ, start_response):
        assert not environ['wsgi.multiprocess'], (
            "The EvalException middleware is not usable in a multi-process environment")
        self.lock.acquire()
        try:
            if self.debugging:
                return self.debug(environ, start_response)
            else:
                return self.respond(environ, start_response)
        finally:
            self.lock.release()

    def debug(self, *args):
        return self.respond(*args)

    def respond(self, environ, start_response):
        base_path = environ['SCRIPT_NAME']
        environ['paste.throw_errors'] = True
        started = []
        def detect_start_response(status, headers, exc_info=None):
            try:
                return start_response(status, headers, exc_info)
            except:
                raise
            else:
                started.append(True)
        try:
            __traceback_supplement__ = errormiddleware.Supplement, self, environ
            app_iter = self.application(environ, detect_start_response)
            return self.catching_iter(app_iter, environ)
        except:
            self.exc_info = exc_info = sys.exc_info()
            self.debugging = True
            for expected in environ.get('paste.expected_exceptions', []):
                if issubclass(exc_info[0], expected):
                    raise
            if not started:
                start_response('500 Internal Server Error',
                               [('content-type', 'text/html')],
                               exc_info)
            # @@: it would be nice to deal with bad content types here
            exc_data = collector.collect_exception(*exc_info)
            html = format_eval_html(exc_data, base_path)
            head_html = (formatter.error_css + formatter.hide_display_js)
            head_html += self.eval_javascript(base_path)
            page = error_template % {
                'head_html': head_html,
                'body': html}
            return [page]

    def catching_iter(self, app_iter, environ):
        __traceback_supplement__ = errormiddleware.Supplement, self, environ
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

    def eval_javascript(self, base_path):
        f = open(os.path.join(os.path.dirname(__file__),
                              'evalexception.js'))
        js = f.read()
        f.close()
        return ('<script type="text/javascript">\n'
                'debug_base = %r;\n' % base_path
                + js
                + '\n</script>\n')

class EvalHTMLFormatter(formatter.HTMLFormatter):

    def __init__(self, base_path, **kw):
        super(EvalHTMLFormatter, self).__init__(**kw)
        self.base_path = base_path
        self.framecount = -1
    
    def format_source_line(self, filename, modname, lineno, name):
        line = formatter.HTMLFormatter.format_source_line(
            self, filename, modname, lineno, name)
        self.framecount += 1
        return (line +
                '  <a href="#" frameid="%s" onClick="show_frame(this)">[+]</a>'
                % self.framecount)

def format_eval_html(exc_data, base_path):
    short_er = EvalHTMLFormatter(
        base_path=base_path,
        include_reusable=False).format_collected_data(exc_data)
    long_er = EvalHTMLFormatter(
        base_path=base_path,
        show_hidden_frames=True,
        show_extra_data=False,
        include_reusable=False).format_collected_data(exc_data)
    return """
    %s
    <br>
    <script type="text/javascript">
    show_button('full_traceback', 'full traceback')
    </script>
    <div id="full_traceback" class="hidden-data">
    %s
    </div>
    """ % (short_er, long_er)


error_template = """
<html>
<head>
 <title>Server Error</title>
 %(head_html)s
</head>
<body>

%(body)s

</body>
</html>
"""
