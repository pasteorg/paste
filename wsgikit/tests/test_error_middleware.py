from fixture import *
from wsgikit.error_middleware import ErrorMiddleware
from wsgikit import lint

def do_request(app, expect_status=500):
    res = fake_request(ErrorMiddleware(lint.middleware(app)),
                       **{'wsgikit.config': {'debug': True}})
    assert res.status_int == expect_status
    return res

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

def test_makes_exception():
    res = do_request(bad_app)
    print res
    assert '<html' in res
    assert 'bad_app() takes no arguments (2 given' in res
    assert 'iterator = application(environ, start_response_wrapper)' in res
    assert 'lint.py' in res
    assert 'error_middleware.py' in res

def test_start_res():
    res = do_request(start_response_app)
    print res
    assert 'ValueError: hi' in res
    assert 'test_error_middleware.py' in res
    assert 'line 17 in <tt>start_response_app</tt>' in res

def test_after_start():
    res = do_request(after_start_response_app, 200)
    print res
    assert 'ValueError: error2' in res
    assert 'line 21' in res

def test_iter_app():
    res = do_request(iter_app, 200)
    print res
    assert 'None raises error' in res
    assert 'yielder' in res
    
                      

    
