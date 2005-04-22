"""
Test fixture for Paste/WebKit testing.

Maybe look at paste.tests.fixture as an alternative to this
"""

from cStringIO import StringIO
from paste import recursive
from paste import session
from paste import httpexceptions
from paste import lint
from paste import wsgilib

_default_environ = {
    'SCRIPT_NAME': '',
    'SERVER_NAME': 'localhost',
    'SERVER_PORT': '80',
    'REQUEST_METHOD': 'GET',
    'HTTP_HOST': 'localhost:80',
    'CONTENT_LENGTH': '0',
    'wsgi.input': StringIO(''),
    'wsgi.version': (1, 0),
    'wsgi.multithread': False,
    'wsgi.multiprocess': False,
    'wsgi.run_once': False,
}

def stack(application):
    """
    Creates a WebKit stack, except with a fixed application and
    no URLParser.
    """
    return recursive.middleware(
        lint.middleware(
        httpexceptions.middleware(
        lint.middleware(
        session.middleware(
        lint.middleware(application))))))

def in_request(application, **kw):
    """
    Used to wrap a function in an application invokation, used like::

        @in_request(my_app, path_info='/whatever',
                    wsgi__input='post-data',
                    REQUEST_METHOD='POST')
        def test_this(output, **kw):
            assert 'I got post-data' in output

    The wrapped function received several keyword arguments, and in
    the future there may be more, so a **kw is required so that
    extra arguments may be ignored.
    """
    def decorator(func):
        def replacement_func(*inner_args, **inner_kw):
            # Note, *inner_args and **inner_kw are intended for use
            # with @param or other py.test parameterizers
            app = stack(application)
            status, headers, output, errors = wsgilib.raw_interactive(
                app, **kw)
            return func(status=status, headers=headers, output=output,
                        errors=errors, application=application,
                        *inner_args,
                        **inner_kw)
        return replacement_func
    return decorator
