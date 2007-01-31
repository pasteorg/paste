# (c) 2005 Ben Bangert
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
from paste.fixture import *
from paste.request import *
from paste.wsgiwrappers import WSGIRequest
from py.test import raises

def simpleapp(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    request = WSGIRequest(environ)
    return ['Hello world!\n', 'The get is %s' % str(request.GET),
        ' and Val is %s' % request.GET.get('name'),
        'The languages are: %s' % request.languages]

def test_gets():
    app = TestApp(simpleapp)
    res = app.get('/')
    assert 'Hello' in res
    assert "get is MultiDict([])" in res
    
    res = app.get('/?name=george')
    res.mustcontain("get is MultiDict([('name', 'george')])")
    res.mustcontain("Val is george")

def test_language_parsing():
    app = TestApp(simpleapp)
    res = app.get('/')
    assert "The languages are: ['en-us']" in res
    