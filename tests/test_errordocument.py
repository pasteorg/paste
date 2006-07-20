"""
Error Document Support Test
+++++++++++++++++++++++++++

WARNING: These tests aren't yet finished. A call to test_ok() using
not_found_app rather than simple_app currently fails complaining of
start_response not having been called before content is returned.

This isn't the full story since start_response will have been called
by the original response but I need advice on how to modify the 
test suite to be able to test this.

I also need to find out how to test that another response was
correctly requested by the middleware.
"""
import os
from paste.errordocument import forward, custom_forward
from paste.fixture import *

def simple_app(environ, start_response):
    start_response("200 OK", [('Content-type', 'text/plain')])
    return ['requested page returned']

def not_found_app(environ, start_response):
    start_response("404 Not found", [('Content-type', 'text/plain')])
    return ['requested page returned']
    
def test_ok():
    app = TestApp(forward(simple_app, codes={404:'/error'}))
    res = app.get('')
    assert res.header('content-type') == 'text/plain'
    assert res.full_status == '200 OK'
    assert 'requested page returned' in res
