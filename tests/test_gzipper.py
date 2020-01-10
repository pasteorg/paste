from paste.fixture import TestApp
from paste.gzipper import middleware
import gzip
import six

def simple_app(environ, start_response):
    start_response('200 OK',
                   [('content-type', 'text/plain'),
                    ('content-length', '0')])
    return [b'this is a test'] if environ['REQUEST_METHOD'] != 'HEAD' else []

wsgi_app = middleware(simple_app)
app = TestApp(wsgi_app)

def test_gzip():
    res = app.get(
        '/', extra_environ=dict(HTTP_ACCEPT_ENCODING='gzip'))
    assert int(res.header('content-length')) == len(res.body)
    assert res.body != b'this is a test'
    actual = gzip.GzipFile(fileobj=six.BytesIO(res.body)).read()
    assert actual == b'this is a test'

def test_gzip_head():
    res = app.head(
        '/', extra_environ=dict(HTTP_ACCEPT_ENCODING='gzip'))
    assert int(res.header('content-length')) == 0
    assert res.body == b''
