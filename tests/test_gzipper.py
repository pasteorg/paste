from paste.fixture import TestApp
from paste.gzipper import middleware
import gzip
import six


def simple_app(environ, start_response):
    start_response('200 OK', [('content-type', 'text/plain')])
    return [b'this is a test']


def simple_app_nothing(environ, start_response):
    start_response('200 OK', [('content-type', 'text/plain')])
    return [b'']


def simple_app_generator(environ, start_response):
    start_response('200 OK', [('content-type', 'text/plain')])
    yield b'this is a test'


def simple_app_generator_nothing(environ, start_response):
    start_response('200 OK', [('content-type', 'text/plain')])
    yield b''


def test_gzip():
    wsgi_app = middleware(simple_app)
    app = TestApp(wsgi_app)
    res = app.get(
        '/', extra_environ=dict(HTTP_ACCEPT_ENCODING='gzip'))
    assert int(res.header('content-length')) == len(res.body)
    assert res.body != b'this is a test'
    actual = gzip.GzipFile(fileobj=six.BytesIO(res.body)).read()
    assert actual == b'this is a test'


def test_gzip_nothing():
    wsgi_app = middleware(simple_app_nothing)
    app = TestApp(wsgi_app)
    res = app.get(
        '/', extra_environ=dict(HTTP_ACCEPT_ENCODING='gzip'))
    assert int(res.header('content-length')) == len(res.body)
    assert res.body != b'this is a test'
    actual = gzip.GzipFile(fileobj=six.BytesIO(res.body)).read()
    assert actual == b''


def test_gzip_generator():
    wsgi_app = middleware(simple_app_generator)
    app = TestApp(wsgi_app)
    res = app.get(
        '/', extra_environ=dict(HTTP_ACCEPT_ENCODING='gzip'))
    assert int(res.header('content-length')) == len(res.body)
    assert res.body != b'this is a test'
    actual = gzip.GzipFile(fileobj=six.BytesIO(res.body)).read()
    assert actual == b'this is a test'


def test_gzip_generator_nothing():
    wsgi_app = middleware(simple_app_generator_nothing)
    app = TestApp(wsgi_app)
    res = app.get(
        '/', extra_environ=dict(HTTP_ACCEPT_ENCODING='gzip'))
    assert int(res.header('content-length')) == len(res.body)
    assert res.body != b'this is a test'
    actual = gzip.GzipFile(fileobj=six.BytesIO(res.body)).read()
    assert actual == b''
