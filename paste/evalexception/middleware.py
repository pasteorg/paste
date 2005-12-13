"""
Exception-catching middleware that allows interactive debugging.

This middleware catches all unexpected exceptions.  A normal
traceback, like produced by
``paste.exceptions.errormiddleware.ErrorMiddleware`` is given, plus
controls to see local variables and evaluate expressions in a local
context.

This can only be used in single-process environments, because
subsequent requests must go back to the same process that the
exception originally occurred in.  Threaded or non-concurrent
environments both work.

This shouldn't be used in production in any way.  That would just be
silly.
"""
import sys
import os
import cgi
import traceback
from cStringIO import StringIO
import pprint
import itertools
import time
import re
from paste.exceptions import errormiddleware, formatter, collector
from paste import wsgilib
from paste import urlparser
from paste import httpexceptions
import evalcontext

limit = 200

def html_quote(v):
    """
    Escape HTML characters, plus translate None to ''
    """
    if v is None:
        return ''
    return cgi.escape(str(v), 1)

def preserve_whitespace(v, quote=True):
    """
    Quote a value for HTML, preserving whitespace (translating
    newlines to ``<br>`` and multiple spaces to use ``&nbsp;``).

    If ``quote`` is true, then the value will be HTML quoted first.
    """
    if quote:
        v = html_quote(v)
    v = v.replace('\n', '<br>\n')
    v = re.sub(r'()(  +)', _repl_nbsp, v)
    v = re.sub(r'(\n)( +)', _repl_nbsp, v)
    v = re.sub(r'^()( +)', _repl_nbsp, v)
    return '<code>%s</code>' % v

def _repl_nbsp(match):
    if len(match.group(2)) == 1:
        return '&nbsp;'
    return match.group(1) + '&nbsp;' * (len(match.group(2))-1) + ' '

def simplecatcher(application):
    """
    A simple middleware that catches errors and turns them into simple
    tracebacks.
    """
    def simplecatcher_app(environ, start_response):
        try:
            return application(environ, start_response)
        except:
            out = StringIO()
            traceback.print_exc(file=out)
            start_response('500 Server Error',
                           [('content-type', 'text/html')],
                           sys.exc_info())
            res = out.getvalue()
            return ['<h3>Error</h3><pre>%s</pre>'
                    % html_quote(res)]
    return simplecatcher_app

def wsgiapp():
    """
    Turns a function or method into a WSGI application.
    """
    def decorator(func):
        def wsgiapp_wrapper(*args):
            # we get 3 args when this is a method, two when it is
            # a function :(
            if len(args) == 3:
                environ = args[1]
                start_response = args[2]
                args = [args[0]]
            else:
                environ, start_response = args
                args = []
            def application(environ, start_response):
                form = wsgilib.parse_formvars(environ)
                headers = wsgilib.ResponseHeaderDict(
                    {'content-type': 'text/html',
                     'status': '200 OK'})
                form['environ'] = environ
                form['headers'] = headers
                res = func(*args, **form)
                status = headers.pop('status')
                start_response(status, headers.headeritems())
                return [res]
            app = httpexceptions.make_middleware(application)
            app = simplecatcher(app)
            return app(environ, start_response)
        wsgiapp_wrapper.exposed = True
        return wsgiapp_wrapper
    return decorator

def get_debug_info(func):
    """
    A decorator (meant to be used under ``wsgiapp()``) that resolves
    the ``debugcount`` variable to a ``DebugInfo`` object (or gives an
    error if it can't be found).
    """
    def debug_info_replacement(self, **form):
        try:
            if 'debugcount' not in form:
                raise ValueError('You must provide a debugcount parameter')
            debugcount = form.pop('debugcount')
            try:
                debugcount = int(debugcount)
            except ValueError:
                raise ValueError('Bad value for debugcount')
            if debugcount not in self.debug_infos:
                raise ValueError(
                    'Debug %s no longer found (maybe it has expired?)'
                    % debugcount)
            debug_info = self.debug_infos[debugcount]
            return func(self, debug_info=debug_info, **form)
        except ValueError, e:
            form['headers']['status'] = '500 Server Error'
            return '<html>There was an error: %s</html>' % html_quote(e)
    return debug_info_replacement
            
debug_counter = itertools.count(int(time.time()))

class EvalException(object):

    def __init__(self, application, global_conf=None,
                 xmlhttp_key=None):
        self.application = application
        self.debug_infos = {}
        if xmlhttp_key is None:
            xmlhttp_key = global_conf.get('xmlhttp_key', '_')
        self.xmlhttp_key = xmlhttp_key

    def __call__(self, environ, start_response):
        assert not environ['wsgi.multiprocess'], (
            "The EvalException middleware is not usable in a "
            "multi-process environment")
        if environ.get('PATH_INFO', '').startswith('/_debug/'):
            return self.debug(environ, start_response)
        else:
            return self.respond(environ, start_response)

    def debug(self, environ, start_response):
        assert wsgilib.path_info_pop(environ) == '_debug'
        next_part = wsgilib.path_info_pop(environ)
        method = getattr(self, next_part, None)
        if not method:
            exc = httpexceptions.HTTPNotFound(
                '%r not found when parsing %r'
                % (next_part, wsgilib.construct_url(environ)))
            return exc.wsgi_application(environ, start_response)
        if not getattr(method, 'exposed', False):
            exc = httpexceptions.HTTPForbidden(
                '%r not allowed' % next_part)
            return exc.wsgi_application(environ, start_response)
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

    #@wsgiapp()
    #@get_debug_info
    def show_frame(self, tbid, debug_info, **kw):
        frame = debug_info.frame(int(tbid))
        vars = frame.tb_frame.f_locals
        if vars:
            local_vars = make_table(vars)
        else:
            local_vars = 'No local vars'
        return input_form(tbid, debug_info) + local_vars

    show_frame = wsgiapp()(get_debug_info(show_frame))

    #@wsgiapp()
    #@get_debug_info
    def exec_input(self, tbid, debug_info, input, **kw):
        if not input.strip():
            return ''
        input = input.rstrip() + '\n'
        frame = debug_info.frame(int(tbid))
        vars = frame.tb_frame.f_locals
        glob_vars = frame.tb_frame.f_globals
        context = evalcontext.EvalContext(vars, glob_vars)
        output = context.exec_expr(input)
        input_html = formatter.str2html(input)
        return ('<code style="color: #060">&gt;&gt;&gt;</code> '
                '<code>%s</code><br>\n%s'
                % (preserve_whitespace(input_html, quote=False),
                   preserve_whitespace(output)))

    exec_input = wsgiapp()(get_debug_info(exec_input))

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
            exc_info = sys.exc_info()
            for expected in environ.get('paste.expected_exceptions', []):
                if issubclass(exc_info[0], expected):
                    raise
                
            if not started:
                start_response('500 Internal Server Error',
                               [('content-type', 'text/html')],
                               exc_info)

            if self.xmlhttp_key:
                get_vars = wsgilib.parse_querystring(environ)
                if dict(get_vars).get(self.xmlhttp_key):
                    exc_data = collector.collect_exception(*exc_info)
                    html = formatter.format_html(
                        exc_data, include_hidden_frames=False,
                        include_reusable=False, show_extra_data=False)
                    return [html]

            count = debug_counter.next()
            debug_info = DebugInfo(count, exc_info)
            assert count not in self.debug_infos
            self.debug_infos[count] = debug_info
            # @@: it would be nice to deal with bad content types here
            exc_data = collector.collect_exception(*exc_info)
            html = format_eval_html(exc_data, base_path, count)
            head_html = (formatter.error_css + formatter.hide_display_js)
            head_html += self.eval_javascript(base_path, count)
            repost_button = make_repost_button(environ)
            page = error_template % {
                'repost_button': repost_button or '',
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
        base_path += '/_debug'
        return (
            '<script type="text/javascript" src="%s/mochikit/MochiKit.js">'
            '</script>\n'
            '<script type="text/javascript" src="%s/media/debug.js">'
            '</script>\n'
            '<script type="text/javascript">\n'
            'debug_base = %r;\n'
            'debug_count = %r;\n'
            '</script>\n'
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

    def frame(self, tbid):
        for frame in self.frames:
            if id(frame) == tbid:
                return frame
        else:
            raise ValueError, (
                "No frame by id %s found from %r" % (tbid, self.frames))

class EvalHTMLFormatter(formatter.HTMLFormatter):

    def __init__(self, base_path, counter, **kw):
        super(EvalHTMLFormatter, self).__init__(**kw)
        self.base_path = base_path
        self.counter = counter
    
    def format_source_line(self, filename, frame):
        line = formatter.HTMLFormatter.format_source_line(
            self, filename, frame)
        return (line +
                '  <a href="#" class="switch_source" '
                'tbid="%s" onClick="return showFrame(this)">&nbsp; &nbsp; '
                '<img src="%s/_debug/media/plus.jpg" border=0 width=9 '
                'height=9> &nbsp; &nbsp;</a>'
                % (frame.tbid, self.base_path))

def make_table(items):
    if isinstance(items, dict):
        items = items.items()
        items.sort()
    rows = []
    i = 0
    for name, value in items:
        i += 1
        out = StringIO()
        pprint.pprint(value, out)
        value = html_quote(out.getvalue())
        if len(value) > 100:
            # @@: This can actually break the HTML :(
            # should I truncate before quoting?
            orig_value = value
            value = value[:100]
            value += '<a class="switch_source" style="background-color: #999" href="#" onclick="return expandLong(this)">...</a>'
            value += '<span style="display: none">%s</span>' % orig_value[100:]
        value = formatter.make_wrappable(value)
        if i % 2:
            attr = ' class="even"'
        else:
            attr = ' class="odd"'
        rows.append('<tr%s style="vertical-align: top;"><td>'
                    '<b>%s</b></td><td style="overflow: auto">%s<td></tr>'
                    % (attr, html_quote(name),
                       preserve_whitespace(value, quote=False)))
    return '<table>%s</table>' % (
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

def make_repost_button(environ):
    url = wsgilib.construct_url(environ)
    if environ['REQUEST_METHOD'] == 'GET':
        return ('<button onclick="window.location.href=%r">'
                'Re-GET Page</button><br>' % url)
    else:
        # @@: I'd like to reconstruct this, but I can't because
        # the POST body is probably lost at this point, and
        # I can't get it back :(
        return None
    fields = []
    for name, value_list in wsgilib.parse_formvars(
        environ, all_as_list=True, include_get_vars=False).items():
        for value in value_list:
            if hasattr(value, 'filename'):
                # @@: Arg, we'll just submit the body, and leave out
                # the filename :(
                value = value.value
            fields.append(
                '<input type="hidden" name="%s" value="%s">'
                % (html_quote(name), html_quote(value)))
    return '''
<form action="%s" method="POST">
%s
<input type="submit" value="Re-POST Page">
</form>''' % (url, '\n'.join(fields))
    

def input_form(tbid, debug_info):
    return '''
<form action="#" method="POST"
 onsubmit="return submitInput($(\'submit_%(tbid)s\'), %(tbid)s)">
<div id="exec-output-%(tbid)s" style="width: 95%%;
 padding: 5px; margin: 5px; border: 2px solid #000;
 display: none"></div>
<input type="text" name="input" id="debug_input_%(tbid)s"
 style="width: 100%%"
 autocomplete="off" onkeypress="upArrow(this, event)"><br>
<input type="submit" value="Execute" name="submitbutton"
 onclick="return submitInput(this, %(tbid)s)"
 id="submit_%(tbid)s"
 input-from="debug_input_%(tbid)s"
 output-to="exec-output-%(tbid)s">
<input type="submit" value="Expand"
 onclick="return expandInput(this)">
</form>
 ''' % {'tbid': tbid}

error_template = '''
<html>
<head>
 <title>Server Error</title>
 %(head_html)s
</head>
<body>

<div id="error-area" style="display: none; background-color: #600; color: #fff; border: 2px solid black">
<div id="error-container"></div>
<button onclick="return clearError()">clear this</button>
</div>

%(repost_button)s

%(body)s

</body>
</html>
'''
