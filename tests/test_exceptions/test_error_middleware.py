from paste.fixture import *
from paste.exceptions.errormiddleware import ErrorMiddleware
from paste import lint

def strip_html(s):
    s = re.sub('<.*?>', '', s)
    s = s.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
    return s

def do_request(app, expect_status=500):
    app = lint.middleware(app)
    app = ErrorMiddleware(app, {}, debug=True)
    app = clear_middleware(app)
    testapp = TestApp(app)
    res = testapp.get('', status=expect_status,
                      expect_errors=True)
    return res

def clear_middleware(app):
    """
    The fixture sets paste.throw_errors, which suppresses exactly what
    we want to test in this case.
    """
    def clear_throw_errors(environ, start_response):
        def replacement(status, headers, exc_info=None):
            return start_response(status, headers)
        if 'paste.throw_errors' in environ:
            del environ['paste.throw_errors']
        return app(environ, replacement)
    return clear_throw_errors
    

############################################################
## Applications that raise exceptions
############################################################

def bad_app():
    "No argument list!"
    return None

def start_response_app(environ, start_response):
    "raise error before start_response"
    raise ValueError("hi")

def after_start_response_app(environ, start_response):
    start_response("200 OK", [('Content-type', 'text/plain')])
    raise ValueError('error2')

def iter_app(environ, start_response):
    start_response("200 OK", [('Content-type', 'text/plain')])
    return yielder(['this', ' is ', ' a', None])

def yielder(args):
    for arg in args:
        if arg is None:
            raise ValueError("None raises error")
        yield arg

############################################################
## Tests
############################################################

def test_makes_exception():
    res = do_request(bad_app)
    assert '<html' in res
    res = strip_html(str(res))
    print res
    assert 'bad_app() takes no arguments (2 given' in res
    assert 'iterator = application(environ, start_response_wrapper)' in res
    assert 'paste.lint' in res
    assert 'paste.exceptions.errormiddleware' in res

def test_start_res():
    res = do_request(start_response_app)
    res = strip_html(str(res))
    print res
    assert 'ValueError: hi' in res
    assert 'test_error_middleware' in res
    assert ':43 in start_response_app' in res

def test_after_start():
    res = do_request(after_start_response_app, 200)
    res = strip_html(str(res))
    print res
    assert 'ValueError: error2' in res
    assert ':47' in res

def test_iter_app():
    res = do_request(iter_app, 200)
    print res
    assert 'None raises error' in res
    assert 'yielder' in res
    
                      

    
