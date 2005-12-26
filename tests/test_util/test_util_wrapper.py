# (c) 2005 Ian Bicking, Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# Some of this code was funded by http://prometheusresearch.com

from paste.util.wrapper import wrap

def test_environ():
    environ = {'HTTP_VIA':'bing', 'wsgi.version': '1.0' }
    d = wrap(environ)
    assert 'bing' == d.GET_HTTP_VIA()
    d.SET_HTTP_HOST('womble')
    assert 'womble' == d.GET_HTTP_HOST()
    assert 'womble' == d.HTTP_HOST
    d.HTTP_HOST = 'different'
    assert 'different' == environ['HTTP_HOST']
    assert None == d.GET_REMOTE_USER()
    assert None == d.REMOTE_USER
    assert '1.0' == d.version
    assert None == d.multiprocess

def test_response_headers():
    response_headers = []
    d = wrap(response_headers)
    assert None == d.CONTENT_TYPE
    d.CONTENT_TYPE = 'text/plain'
    assert response_headers == [('content-type','text/plain')]
    assert d.CONTENT_TYPE == 'text/plain'
    d.CONTENT_TYPE = 'text/html'
    assert response_headers == [('content-type','text/html')]
    assert d.CONTENT_TYPE == 'text/html'
    assert None == getattr(d,'SET_COOKIE',None) # multi-entity header
