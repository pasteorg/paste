# (c) 2005 Ian Bicking, Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# Some of this code was funded by http://prometheusresearch.com

from paste.util.wrapper import wrap

def test_environ():
    d = wrap({'HTTP_VIA':'bing', 'wsgi.version': '1.0' })
    assert 'bing' == d.GET_HTTP_VIA()
    d.SET_HTTP_HOST('womble')
    assert 'womble' == d.GET_HTTP_HOST()
    assert 'womble' == d.HTTP_HOST
    d.HTTP_HOST = 'different'
    assert 'different' == d['HTTP_HOST']
    assert None == d.GET_REMOTE_USER()
    assert None == d.REMOTE_USER
    assert '1.0' == d.version
    assert None == d.multiprocess

