import sys
import os
import threading
import cgi
import traceback
from cStringIO import StringIO
import pprint
import itertools
import time
import cgi
from paste.exceptions import errormiddleware, formatter, collector
from paste import wsgilib
from paste import urlparser
from paste import httpexceptions
import evalcontext

limit = 200

def html_quote(v):
    if v is None:
        return ''
    return cgi.escape(str(v), 1)

def wsgiapp():
    """
    Turns a function or method into a 
    """
    def decorator(func):
        def application(*args):
            if len(args) == 3:
                environ = args[1]
                start_response = args[2]
                args = [args[0]]
            else:
                environ, start_response = args
                args = []
            fs = cgi.FieldStorage(
                fp=environ['wsgi.input'],
                environ=environ,
                keep_blank_values=1)
            form = {}
            for name in fs.keys():
                value = fs[name]
                if not value.filename:
                    value = value.value
                if name in form:
                    if isinstance(form[name], list):
                        form[name].append(value)
                    else:
                        form[name] = [form[name], value]
                else:
                    form[name] = value
            headers = HeaderDict({'content-type': 'text/html',
                                  'status': '200 OK'})
            form['environ'] = environ
            form['headers'] = headers
            res = func(*args, **form)
            status = headers['status']
            del headers['status']
            start_response(status, headers.headeritems())
            return [res]
        application.exposed = True
        return application
    return decorator

def get_debug_info(func):
    def replacement(self, **form):
        try:
            if 'debugcount' not in form:
                raise ValueError('You must provide a debugcount parameter')
            debugcount = form.pop('debugcount')
            try:
                debugcount = int(debugcount)
            except ValueError:
                raise ValueError('Bad value for debugcount')
            if debugcount not in self.debug_infos:
                raise ValueError('Debug %s no longer found (maybe it has expired?)' % debugcount)
            debug_info = self.debug_infos[debugcount]
            return func(self, debug_info=debug_info, **form)
        except ValueError, e:
            form['headers']['status'] = '500 Server Error'
            return '<html>There was an error: %s</html>' % e
    return replacement
            

class HeaderDict(dict):

    def __getitem__(self, key):
        return dict.__getitem__(self, key.lower())

    def __setitem__(self, key, value):
        dict.__setitem__(self, key.lower(), value)

    def __delitem__(self, key):
        dict.__delitem__(self, key.lower())

    def add(self, key, value):
        key = key.lower()
        if key in self:
            if isinstance(self[key], list):
                self[key].append(value)
            else:
                self[key] = [self[key], value]
        else:
            self[key] = value

    def headeritems(self):
        result = []
        for key in self:
            if isinstance(self[key], list):
                for v in self[key]:
                    result.append((key, v))
            else:
                result.append((key, self[key]))
        return result

debug_counter = itertools.count(int(time.time()))

class EvalException(object):

    def __init__(self, application, global_conf=None):
        self.application = application
        self.debug_infos = {}

    def __call__(self, environ, start_response):
        assert not environ['wsgi.multiprocess'], (
            "The EvalException middleware is not usable in a multi-process environment")
        if environ.get('PATH_INFO', '').startswith('/_debug/'):
            return self.debug(environ, start_response)
        else:
            return self.respond(environ, start_response)

    def debug(self, environ, start_response):
        assert wsgilib.path_info_pop(environ) == '_debug'
        next_part = wsgilib.path_info_pop(environ)
        method = getattr(self, next_part, None)
        if not method:
            return wsgilib.error_response_app(
                '404 Not Found', '%r not found' % next_part)(
                environ, start_response)
        if not getattr(method, 'exposed', False):
            return wsgilib.error_response_app(
                '403 Forbidden', '%r not allowed' % next_part)(
                environ, start_response)
        return method(environ, start_response)

    def media(self, environ, start_response):
        app = urlparser.StaticURLParser(
            os.path.join(os.path.dirname(__file__), 'media'))
        return app(environ, start_response)
    media.exposed = True

    def mochikit(self, environ, start_response):
        app = urlparser.StaticURLParser(
            os.path.join(os.path.dirname(__file__), 'mochikit', 'MochiKit'))
        return app(environ, start_response)
    mochikit.exposed = True

    @wsgiapp()
    @get_debug_info
    def show_frame(self, framecount, debug_info, **kw):
        frame = debug_info.frames[int(framecount)]
        vars = frame.tb_frame.f_locals
        if vars:
            local_vars = make_table(vars)
        else:
            local_vars = 'No local vars'
        return local_vars + input_form(framecount, debug_info)

    @wsgiapp()
    @get_debug_info
    def exec_input(self, framecount, debug_info, input, **kw):
        frame = debug_info.frames[int(framecount)]
        vars = frame.tb_frame.f_locals
        context = evalcontext.EvalContext(vars)
        output = context.exec_expr(input)
        return '>>> %s\n%s' % (input, output)

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
            for expected in environ.get('paste.expected_exceptions', []):
                if issubclass(exc_info[0], expected):
                    raise
            exc_info = sys.exc_info()
            count = debug_counter.next()
            debug_info = DebugInfo(count, exc_info)
            assert count not in self.debug_infos
            self.debug_infos[count] = debug_info
            if not started:
                start_response('500 Internal Server Error',
                               [('content-type', 'text/html')],
                               exc_info)
            # @@: it would be nice to deal with bad content types here
            exc_data = collector.collect_exception(*exc_info)
            html = format_eval_html(exc_data, base_path, count)
            head_html = (formatter.error_css + formatter.hide_display_js)
            head_html += self.eval_javascript(base_path, count)
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

    def eval_javascript(self, base_path, counter):
        return ('<script type="text/javascript" src="%s/_debug/mochikit/MochiKit.js"></script>\n'
                '<script type="text/javascript" src="%s/_debug/media/debug.js"></script>\n'
                '<script type="text/javascript">\n'
                'debug_base = %r;\n'
                'debug_count = %r;\n'
                '\n</script>\n'
                % (base_path, base_path, base_path, counter))

class DebugInfo(object):

    def __init__(self, counter, exc_info):
        self.counter = counter
        self.exc_type, self.exc_value, self.tb = exc_info
        __exception_formatter__ = 1
        self.frames = []
        n = 0
        tb = self.tb
        while tb is not None and (limit is None or n < limit):
            if tb.tb_frame.f_locals.get('__exception_formatter__'):
                # Stop recursion. @@: should make a fake ExceptionFrame
                break
            self.frames.append(tb)
            tb = tb.tb_next
            n += 1

class EvalHTMLFormatter(formatter.HTMLFormatter):

    def __init__(self, base_path, counter, **kw):
        super(EvalHTMLFormatter, self).__init__(**kw)
        self.base_path = base_path
        self.counter = counter
        self.framecount = -1
    
    def format_source_line(self, filename, modname, lineno, name):
        line = formatter.HTMLFormatter.format_source_line(
            self, filename, modname, lineno, name)
        self.framecount += 1
        return (line +
                '  <a href="#" framecount="%s" onClick="show_frame(this)">[+]</a>'
                % self.framecount)

def make_table(items):
    if isinstance(items, dict):
        items = items.items()
        items.sort()
    rows = []
    for name, value in items:
        out = StringIO()
        pprint.pprint(value, out)
        value = html_quote(out.getvalue())
        value = formatter.make_pre_wrappable(value)
        rows.append('<tr><td>%s</td><td><pre style="overflow: auto">%s</pre><td></tr>'
                    % (html_quote(name), value))
    return '<table border="1">%s</table>' % (
        '\n'.join(rows))

def format_eval_html(exc_data, base_path, counter):
    short_er = EvalHTMLFormatter(
        base_path=base_path,
        counter=counter,
        include_reusable=False).format_collected_data(exc_data)
    long_er = EvalHTMLFormatter(
        base_path=base_path,
        counter=counter,
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


def input_form(framecount, debug_info):
    return '''
<form action="#" method="POST"
 onsubmit="return submit_input($(\'submit_%(framecount)s\'), %(framecount)s)">
<textarea disabled="disabled" rows=5 cols=60 style="width: 100%%"
 id="debug_output_%(framecount)s"></textarea><br>
<input type="text" name="input" id="debug_input_%(framecount)s"
 style="width: 100%%"><br>
<input type="submit" value="Execute"
 onclick="return submit_input(this, %(framecount)s)"
 id="submit_%(framecount)s"
 input-from="debug_input_%(framecount)s"
 output-to="debug_output_%(framecount)s">
</form>
 ''' % {'framecount': framecount}

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
