# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

"""
A module of many disparate routines.
"""

# functions which moved to paste.request
from request import get_cookies, parse_querystring, parse_formvars
from request import construct_url, path_info_split, path_info_pop

from Cookie import SimpleCookie
from cStringIO import StringIO
import mimetypes
import os
import cgi
import sys
import re
from urlparse import urlsplit
import warnings

__all__ = ['get_cookies', 'add_close', 'raw_interactive',
           'interactive', 'construct_url', 'error_body_response',
           'error_response', 'send_file', 'has_header', 'header_value',
           'path_info_split', 'path_info_pop', 'capture_output',
           'catch_errors', 'dump_environ']


class add_close:
    """
    An an iterable that iterates over app_iter, then calls
    close_func.
    """
    
    def __init__(self, app_iterable, close_func):
        self.app_iterable = app_iterable
        self.app_iter = iter(app_iterable)
        self.close_func = close_func

    def __iter__(self):
        return self

    def next(self):
        return self.app_iter.next()

    def close(self):
        if hasattr(self.app_iterable, 'close'):
            self.app_iterable.close()
        self.close_func()

def catch_errors(application, environ, start_response, error_callback,
                 ok_callback=None):
    """
    Runs the application, and returns the application iterator (which should be
    passed upstream).  If an error occurs then error_callback will be called with
    exc_info as its sole argument.  If no errors occur and ok_callback is given,
    then it will be called with no arguments.
    """
    error_occurred = False
    try:
        app_iter = application(environ, start_response)
    except:
        error_callback(sys.exc_info())
        raise
    if type(app_iter) in (list, tuple):
        # These won't produce exceptions
        if ok_callback:
            ok_callback()
        return app_iter
    else:
        return _wrap_app_iter(app_iter, error_callback, ok_callback)

class _wrap_app_iter(object):

    def __init__(self, app_iterable, error_callback, ok_callback):
        self.app_iterable = app_iterable
        self.app_iter = iter(app_iterable)
        self.error_callback = error_callback
        self.ok_callback = ok_callback
        if hasattr(self.app_iterable, 'close'):
            self.close = self.app_iterable.close

    def __iter__(self):
        return self

    def next(self):
        try:
            return self.app_iter.next()
        except StopIteration:
            if self.ok_callback:
                self.ok_callback()
            raise
        except:
            self.error_callback(sys.exc_info())
            raise

def raw_interactive(application, path='', **environ):
    """
    Runs the application in a fake environment.
    """
    assert "path_info" not in environ, "argument list changed"
    errors = StringIO()
    basic_environ = {
        # mandatory CGI variables
        'REQUEST_METHOD': 'GET',     # always mandatory
        'SCRIPT_NAME': '',           # may be empty if app is at the root
        'PATH_INFO': '',             # may be empty if at root of app
        'SERVER_NAME': 'localhost',  # always mandatory
        'SERVER_PORT': '80',         # always mandatory 
        'SERVER_PROTOCOL': 'HTTP/1.0',
        # mandatory wsgi variables
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.input': StringIO(''),
        'wsgi.errors': errors,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        }
    if path:
        (_,_,path_info,query,fragment) = urlsplit(str(path))
        basic_environ['PATH_INFO'] = path_info
        if query:
            basic_environ['QUERY_STRING'] = query
    for name, value in environ.items():
        name = name.replace('__', '.')
        basic_environ[name] = value
    istream = basic_environ['wsgi.input']
    if isinstance(istream, str):
        basic_environ['wsgi.input'] = StringIO(istream)
        basic_environ['CONTENT_LENGTH'] = len(istream)
    data = {}
    output = StringIO()
    headers_set = []
    headers_sent = []
    def start_response(status, headers, exc_info=None):
        if exc_info:
            try:
                if headers_sent:
                    # Re-raise original exception only if headers sent
                    raise exc_info[0], exc_info[1], exc_info[2]
                else:
                    # We assume that the sender, who is probably setting
                    # the headers a second time /w a 500 has produced
                    # a more appropriate response.
                    pass
            finally:
                # avoid dangling circular reference
                exc_info = None
        elif headers_set:
            # You cannot set the headers more than once, unless the
            # exc_info is provided.
            raise AssertionError("Headers already set and no exc_info!")
        headers_set.append(True)
        data['status'] = status
        data['headers'] = headers
        return output.write
    app_iter = application(basic_environ, start_response)
    try:
        try:
            for s in app_iter:
                headers_sent.append(True)
                if not headers_set:
                    raise AssertionError("Content sent w/o headers!")
                output.write(s)
        except TypeError, e:
            # Typically "iteration over non-sequence", so we want
            # to give better debugging information...
            e.args = ((e.args[0] + ' iterable: %r' % app_iter),) + e.args[1:]
            raise
    finally:
        if hasattr(app_iter, 'close'):
            app_iter.close()
    return (data['status'], data['headers'], output.getvalue(),
            errors.getvalue())

def interactive(*args, **kw):
    """
    Runs the application interatively, wrapping `raw_interactive` but
    returning the output in a formatted way.
    """
    status, headers, content, errors = raw_interactive(*args, **kw)
    full = StringIO()
    if errors:
        full.write('Errors:\n')
        full.write(errors.strip())
        full.write('\n----------end errors\n')
    full.write(status + '\n')
    for name, value in headers:
        full.write('%s: %s\n' % (name, value))
    full.write('\n')
    full.write(content)
    return full.getvalue()
interactive.proxy = 'raw_interactive'

def dump_environ(environ,start_response):
    """ 
    Application which simply dumps the current environment
    variables out as a plain text response.
    """
    output = []
    keys = environ.keys()
    keys.sort()
    for k in keys:
        v = str(environ[k]).replace("\n","\n    ")
        output.append("%s: %s\n" % (k,v))
    output = "".join(output)
    headers = [('Content-Type', 'text/plain'),
               ('Content-Length', len(output))]
    start_response("200 OK",headers)
    return [output]

def error_body_response(error_code, message, __warn=True):
    """
    Returns a standard HTML response page for an HTTP error.
    """
    if __warn:
        warnings.warn(
            'wsgilib.error_body_response is deprecated; use the '
            'wsgi_application method on an HTTPException object '
            'instead', DeprecationWarning, 1)
    return '''\
<html>
  <head>
    <title>%(error_code)s</title>
  </head>
  <body>
  <h1>%(error_code)s</h1>
  %(message)s
  </body>
</html>''' % {
        'error_code': error_code,
        'message': message,
        }

def error_response(environ, error_code, message,
                   debug_message=None, __warn=True):
    """
    Returns the status, headers, and body of an error response.

    Use like::

        status, headers, body = wsgilib.error_response(
            '301 Moved Permanently', 'Moved to <a href="%s">%s</a>'
            % (url, url))
        start_response(status, headers)
        return [body]
    """
    if __warn:
        warnings.warn(
            'wsgilib.error_response is deprecated; use the '
            'wsgi_application method on an HTTPException object '
            'instead', DeprecationWarning, 1)
    if debug_message and environ.get('paste.config', {}).get('debug'):
        message += '\n\n<!-- %s -->' % debug_message
    body = error_body_response(error_code, message, __warn=False)
    headers = [('content-type', 'text/html'),
               ('content-length', str(len(body)))]
    return error_code, headers, body

def error_response_app(error_code, message, debug_message=None,
                       __warn=True):
    """
    An application that emits the given error response.
    """
    if __warn:
        warnings.warn(
            'wsgilib.error_response_app is deprecated; use the '
            'wsgi_application method on an HTTPException object '
            'instead', DeprecationWarning, 1)
    def application(environ, start_response):
        status, headers, body = error_response(
            environ, error_code, message,
            debug_message=debug_message, __warn=False)
        start_response(status, headers)
        return [body]
    return application

def send_file(filename):
    """
    Returns an application that will send the file at the given
    filename.  Adds a mime type based on ``mimetypes.guess_type()``.
    """
    # @@: Should test things like last-modified, if-modified-since,
    # etc.
    
    def application(environ, start_response):
        type, encoding = mimetypes.guess_type(filename)
        # @@: I don't know what to do with the encoding.
        if not type:
            type = 'application/octet-stream'
        size = os.stat(filename).st_size
        try:
            file = open(filename, 'rb')
        except (IOError, OSError), e:
            status, headers, body = error_response(
                '403 Forbidden',
                'You are not permitted to view this file (%s)' % e)
            start_response(status, headers)
            return [body]
        start_response('200 OK',
                       [('content-type', type),
                        ('content-length', str(size))])
        return _FileIter(file)

    return application

class _FileIter:

    def __init__(self, fp, blocksize=4096):
        self.file = fp
        self.blocksize = blocksize

    def __iter__(self):
        return self

    def next(self):
        data = self.file.read(self.blocksize)
        if not data:
            raise StopIteration
        return data

    def close(self):
        self.file.close()

def has_header(headers, name):
    """
    Is header named ``name`` present in headers?
    """
    name = name.lower()
    for header, value in headers:
        if header.lower() == name:
            return True
    return False

def header_value(headers, name):
    """
    Returns the header's value, or None if no such header.  If a
    header appears more than once, all the values of the headers
    are joined with ','
    """
    name = name.lower()
    result = [value for header, value in headers
              if header.lower() == name]
    if result:
        return ','.join(result)
    else:
        return None

def remove_header(headers, name):
    """
    Removes the named header from the list of headers.  Returns the
    value of that header, or None if no header found.  If multiple
    headers are found, only the last one is returned.
    """
    name = name.lower()
    i = 0
    result = None
    while i < len(headers):
        if headers[i][0].lower() == name:
            result = headers[i][1]
            del headers[i]
            continue
        i += 1
    return result


def capture_output(environ, start_response, application):
    """
    Runs application with environ and start_response, and captures
    status, headers, and body.

    Sends status and header, but *not* body.  Returns (status,
    headers, body).  Typically this is used like::

        def dehtmlifying_middleware(application):
            def replacement_app(environ, start_response):
                status, headers, body = capture_output(
                    environ, start_response, application)
                content_type = header_value(headers, 'content-type')
                if (not content_type
                    or not content_type.startswith('text/html')):
                    return [body]
                body = re.sub(r'<.*?>', '', body)
                return [body]
            return replacement_app
    """
    warnings.warn(
        'wsgilib.capture_output has been deprecated in favor '
        'of wsgilib.intercept_output',
        DeprecationWarning, 2)
    data = []
    output = StringIO()
    def replacement_start_response(status, headers, exc_info=None):
        if data:
            data[:] = []
        data.append(status)
        data.append(headers)
        start_response(status, headers, exc_info)
        return output.write
    app_iter = application(environ, replacement_start_response)
    try:
        for item in app_iter:
            output.write(item)
    finally:
        if hasattr(app_iter, 'close'):
            app_iter.close()
    if not data:
        data.append(None)
    if len(data) < 2:
        data.append(None)
    data.append(output.getvalue())
    return data

def intercept_output(environ, application):
    """
    Runs application with environ and captures status, headers, and
    body.  None are sent on; you must send them on yourself (unlike
    ``capture_output``)

    Typically this is used like::

        def dehtmlifying_middleware(application):
            def replacement_app(environ, start_response):
                status, headers, body = capture_output(
                    environ, start_response, application)
                content_type = header_value(headers, 'content-type')
                if (not content_type
                    or not content_type.startswith('text/html')):
                    return [body]
                body = re.sub(r'<.*?>', '', body)
                return [body]
            return replacement_app
    """
    data = []
    output = StringIO()
    def replacement_start_response(status, headers, exc_info=None):
        if data:
            data[:] = []
        data.append(status)
        data.append(headers)
        return output.write
    app_iter = application(environ, replacement_start_response)
    try:
        for item in app_iter:
            output.write(item)
    finally:
        if hasattr(app_iter, 'close'):
            app_iter.close()
    if not data:
        data.append(None)
    if len(data) < 2:
        data.append(None)
    data.append(output.getvalue())
    return data

class ResponseHeaderDict(dict):

    """
    This represents response headers.  It handles the normal case
    of headers as a dictionary, with case-insensitive keys.

    Also there is an ``.add(key, value)`` method, which sets the key,
    or adds the value to the current value (turning it into a list if
    necessary).

    For passing to WSGI there is a ``.headerdict()`` method which is
    like ``.items()`` but unpacks those value lists.  It also handles
    encoding -- all headers are encoded in ASCII (if they are
    unicode).

    @@: Should that be ISO-8859-1 or UTF-8?  I'm not sure what the
    spec says.
    """

    def __getitem__(self, key):
        return dict.__getitem__(self, self.normalize(key))

    def __setitem__(self, key, value):
        dict.__setitem__(self, self.normalize(key), value)

    def __delitem__(self, key):
        dict.__delitem__(self, self.normalize(key))

    def __contains__(self, key):
        return dict.__contains__(self, self.normalize(key))

    has_key = __contains__

    def pop(self, key):
        return dict.pop(self, self.normalize(key))

    def update(self, other):
        for key in other:
            self[self.normalize(key)] = other[key]

    def normalize(self, key):
        return str(key).lower().strip()
        
    def add(self, key, value):
        key = self.normalize(key)
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
                    result.append((key, str(v)))
            else:
                result.append((key, str(self[key])))
        return result
        

def _warn_deprecated(new_func):
    new_name = new_func.func_name
    new_path = new_func.func_globals['__name__'] + '.' + new_name
    def replacement(*args, **kw):
        warnings.warn(
            "The function wsgilib.%s has been moved to %s"
            % (new_name, new_path),
            DeprecationWarning, 2)
        return new_func(*args, **kw)
    try:
        replacement.func_name = new_func.func_name
    except:
        pass
    return replacement

# Put warnings wrapper in place for all public functions that
# were imported from elsewhere:

for _name in __all__:
    _func = globals()[_name]
    if (hasattr(_func, 'func_globals')
        and _func.func_globals['__name__'] != __name__):
        globals()[_name] = _warn_deprecated(_func)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    
