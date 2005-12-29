# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

import re
import sys
from types import DictType, StringType, TupleType, ListType
import warnings

header_re = re.compile(r'^[a-zA-Z][a-zA-Z0-9\-_]*$')
bad_header_value_re = re.compile(r'[\000-\037]')

class WSGIWarning(Warning):
    """
    Raised in response to WSGI-spec-related warnings
    """

def middleware(application, global_conf=None):

    """
    When applied between a WSGI server and a WSGI application, this
    middleware will check for WSGI compliancy on a number of levels.
    This middleware does not modify the request or response in any
    way, but will throw an AssertionError if anything seems off
    (except for a failure to close the application iterator, which
    will be printed to stderr -- there's no way to throw an exception
    at that point).
    """
    
    def lint_app(*args, **kw):
        assert len(args) == 2, "Two arguments required"
        assert not kw, "No keyword arguments allowed"
        environ, start_response = args

        check_environ(environ)

        # We use this to check if the application returns without
        # calling start_response:
        start_response_started = []

        def start_response_wrapper(*args, **kw):
            assert len(args) == 2 or len(args) == 3, (
                "Invalid number of arguments: %s" % args)
            assert not kw, "No keyword arguments allowed"
            status = args[0]
            headers = args[1]
            if len(args) == 3:
                exc_info = args[2]
            else:
                exc_info = None

            check_status(status)
            check_headers(headers)
            check_content_type(status, headers)
            check_exc_info(exc_info)

            start_response_started.append(None)
            return WriteWrapper(start_response(*args))

        environ['wsgi.input'] = InputWrapper(environ['wsgi.input'])
        environ['wsgi.errors'] = ErrorWrapper(environ['wsgi.errors'])

        iterator = application(environ, start_response_wrapper)
        assert iterator is not None and iterator != False, (
            "The application must return an iterator, if only an empty list")

        check_iterator(iterator)

        return IteratorWrapper(iterator, start_response_started)

    return lint_app

class InputWrapper:

    def __init__(self, wsgi_input):
        self.input = wsgi_input

    def read(self, *args):
        assert len(args) <= 1
        v = self.input.read(*args)
        assert type(v) is type("")
        return v

    def readline(self):
        v = self.input.readline()
        assert type(v) is type("")
        return v

    def readlines(self, *args):
        assert len(args) <= 1
        lines = self.input.readlines(*args)
        assert type(lines) is type([])
        for line in lines:
            assert type(line) is type("")
        return lines
    
    def __iter__(self):
        while 1:
            line = self.readline()
            if not line:
                return
            yield line

    def close(self):
        assert 0, "input.close() must not be called"

class ErrorWrapper:

    def __init__(self, wsgi_errors):
        self.errors = wsgi_errors

    def write(self, s):
        assert type(s) is type("")
        self.errors.write(s)

    def flush(self):
        self.errors.flush()

    def writelines(self, seq):
        for line in seq:
            self.write(line)

    def close(self):
        assert 0, "errors.close() must not be called"

class WriteWrapper:

    def __init__(self, wsgi_writer):
        self.writer = wsgi_writer

    def __call__(self, s):
        assert type(s) is type("")
        self.writer(s)

class PartialIteratorWrapper:

    def __init__(self, wsgi_iterator):
        self.iterator = wsgi_iterator

    def __iter__(self):
        # We want to make sure __iter__ is called
        return IteratorWrapper(self.iterator)

class IteratorWrapper:

    def __init__(self, wsgi_iterator, check_start_response):
        self.original_iterator = wsgi_iterator
        self.iterator = iter(wsgi_iterator)
        self.closed = False
        self.check_start_response = check_start_response

    def __iter__(self):
        return self

    def next(self):
        assert not self.closed, (
            "Iterator read after closed")
        v = self.iterator.next()
        if self.check_start_response is not None:
            assert self.check_start_response, (
                "The application returns and we started iterating over its body, but start_response has not yet been called")
            self.check_start_response = None
        return v
        
    def close(self):
        self.closed = True
        if hasattr(self.original_iterator, 'close'):
            self.original_iterator.close()

    def __del__(self):
        if not self.closed:
            sys.stderr.write(
                "Iterator garbage collected without being closed")
        assert self.closed, (
            "Iterator garbage collected without being closed")

def check_environ(environ):
    assert type(environ) is DictType, (
        "Environment is not of the right type: %r (environment: %r)"
        % (type(environ), environ))
    
    for key in ['REQUEST_METHOD', 'SERVER_NAME', 'SERVER_PORT',
                'wsgi.version', 'wsgi.input', 'wsgi.errors',
                'wsgi.multithread', 'wsgi.multiprocess',
                'wsgi.run_once']:
        assert key in environ, (
            "Environment missing required key: %r" % key)

    for key in ['HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH']:
        assert key not in environ, (
            "Environment should not have the key: %s "
            "(use %s instead)" % (key, key[5:]))

    if 'QUERY_STRING' not in environ:
        warnings.warn(
            'QUERY_STRING is not in the WSGI environment; the cgi '
            'module will use sys.argv when this variable is missing, '
            'so application errors are more likely',
            WSGIWarning)

    for key in environ.keys():
        if '.' in key:
            # Extension, we don't care about its type
            continue
        assert type(environ[key]) is StringType, (
            "Environmental variable %s is not a string: %r (value: %r)"
            % (type(environ[key]), environ[key]))
        
    assert type(environ['wsgi.version']) is TupleType, (
        "wsgi.version should be a tuple (%r)" % environ['wsgi.version'])
    assert environ['wsgi.url_scheme'] in ('http', 'https'), (
        "wsgi.url_scheme unknown: %r" % environ['wsgi.url_scheme'])

    check_input(environ['wsgi.input'])
    check_errors(environ['wsgi.errors'])

    # @@: these need filling out:
    if environ['REQUEST_METHOD'] not in (
        'GET', 'HEAD', 'POST', 'OPTIONS','PUT','DELETE','TRACE'):
        warnings.warn(
            "Unknown REQUEST_METHOD: %r" % environ['REQUEST_METHOD'],
            WSGIWarning)

    assert (not environ.get('SCRIPT_NAME')
            or environ['SCRIPT_NAME'].startswith('/')), (
        "SCRIPT_NAME doesn't start with /: %r" % environ['SCRIPT_NAME'])
    assert (not environ.get('PATH_INFO')
            or environ['PATH_INFO'].startswith('/')), (
        "PATH_INFO doesn't start with /: %s" % environ['PATH_INFO'])
    if environ.get('CONTENT_LENGTH'):
        assert int(environ['CONTENT_LENGTH']) >= 0, (
            "Invalid CONTENT_LENGTH: %r" % environ['CONTENT_LENGTH'])

    if not environ.get('SCRIPT_NAME'):
        assert environ.has_key('PATH_INFO'), (
            "One of SCRIPT_NAME or PATH_INFO are required (PATH_INFO "
            "should at least be '/' if SCRIPT_NAME is empty)")
    assert environ.get('SCRIPT_NAME') != '/', (
        "SCRIPT_NAME cannot be '/'; it should instead be '', and "
        "PATH_INFO should be '/'")

def check_input(wsgi_input):
    for attr in ['read', 'readline', 'readlines', '__iter__']:
        assert hasattr(wsgi_input, attr), (
            "wsgi.input (%r) doesn't have the attribute %s"
            % (wsgi_input, attr))

def check_errors(wsgi_errors):
    for attr in ['flush', 'write', 'writelines']:
        assert hasattr(wsgi_errors, attr), (
            "wsgi.errors (%r) doesn't have the attribute %s"
            % (wsgi_errors, attr))

def check_status(status):
    assert type(status) is StringType, (
        "Status must be a string (not %r)" % status)
    # Implicitly check that we can turn it into an integer:
    status_code = status.split(None, 1)[0]
    assert len(status_code) == 3, (
        "Status codes must be three characters: %r" % status_code)
    status_int = int(status_code)
    assert status_int >= 100, "Status code is invalid: %r" % status_int
    if len(status) < 4 or status[4] != ' ':
        warnings.warn(
            "The status string (%r) should be a three-digit integer "
            "followed by a single space and a status explanation"
            % status, WSGIWarning)

def check_headers(headers):
    assert type(headers) is ListType, (
        "Headers (%r) must be of type list: %r"
        % (headers, type(headers)))
    header_names = {}
    for item in headers:
        assert type(item) is TupleType, (
            "Individual headers (%r) must be of type tuple: %r"
            % (item, type(item)))
        assert len(item) == 2
        name, value = item
        assert name.lower() != 'status', (
            "The Status header cannot be used; it conflicts with CGI "
            "script, and HTTP status is not given through headers "
            "(value: %r)." % value)
        header_names[name.lower()] = None
        assert '\n' not in name and ':' not in name, (
            "Header names may not contain ':' or '\\n': %r" % name)
        assert header_re.search(name), "Bad header name: %r" % name
        assert not name.endswith('-') and not name.endswith('_'), (
            "Names may not end in '-' or '_': %r" % name)
        assert not bad_header_value_re.search(value), (
            "Bad header value: %r (bad char: %r)"
            % (value, bad_header_value_re.search(value).group(0)))

def check_content_type(status, headers):
    code = int(status.split(None, 1)[0])
    # @@: need one more person to verify this interpretation of RFC 2616
    #     http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
    NO_MESSAGE_BODY = (204, 304)
    for name, value in headers:
        if name.lower() == 'content-type':
            if code not in NO_MESSAGE_BODY:
                return
            assert 0, (("Content-Type header found in a %s response, "
                        "which must not return content.") % code)
    if code not in NO_MESSAGE_BODY:
        assert 0, "No Content-Type header found in headers (%s)" % headers

def check_exc_info(exc_info):
    assert exc_info is None or type(exc_info) is type(()), (
        "exc_info (%r) is not a tuple: %r" % (exc_info, type(exc_info)))
    # More exc_info checks?

def check_iterator(iterator):
    # Technically a string is legal, which is why it's a really bad
    # idea, because it may cause the response to be returned
    # character-by-character
    assert not isinstance(iterator, str), (
        "You should not return a string as your application iterator, "
        "instead return a single-item list containing that string.")

def make_middleware(application, global_conf):
    # @@: global_conf should be taken out of the middleware function,
    # and isolated here
    return middleware(application)

__all__ = ['middleware', 'make_middleware']
