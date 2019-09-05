import email
import io
import socket

import six

from paste.httpserver import LimitedLengthFile, WSGIHandler
from six.moves import StringIO


class MockServer(object):
    server_address = ('127.0.0.1', 80)


class MockSocket(object):
    def makefile(self, mode, bufsize):
        return StringIO()


def test_environ():
    mock_socket = MockSocket()
    mock_client_address = '1.2.3.4'
    mock_server = MockServer()

    wsgi_handler = WSGIHandler(mock_socket, mock_client_address, mock_server)
    wsgi_handler.command = 'GET'
    wsgi_handler.path = '/path'
    wsgi_handler.request_version = 'HTTP/1.0'
    wsgi_handler.headers = email.message_from_string('Host: mywebsite')

    wsgi_handler.wsgi_setup()

    assert wsgi_handler.wsgi_environ['HTTP_HOST'] == 'mywebsite'


def test_environ_with_multiple_values():
    mock_socket = MockSocket()
    mock_client_address = '1.2.3.4'
    mock_server = MockServer()

    wsgi_handler = WSGIHandler(mock_socket, mock_client_address, mock_server)
    wsgi_handler.command = 'GET'
    wsgi_handler.path = '/path'
    wsgi_handler.request_version = 'HTTP/1.0'
    wsgi_handler.headers = email.message_from_string('Host: host1\nHost: host2')

    wsgi_handler.wsgi_setup()

    assert wsgi_handler.wsgi_environ['HTTP_HOST'] == 'host1,host2'


def test_limited_length_file():
    backing = io.BytesIO(b'0123456789')
    f = LimitedLengthFile(backing, 9)
    assert f.tell() == 0
    assert f.read() == b'012345678'
    assert f.tell() == 9
    assert f.read() == b''

def test_limited_length_file_tell_on_socket():
    backing_read, backing_write = socket.socketpair()
    if six.PY2:
        # On Python 2, socketpair() returns an internal socket type rather than
        # the public one.
        backing_read = socket.socket(_sock=backing_read)
    f = LimitedLengthFile(backing_read.makefile('rb'), 10)
    backing_write.send(b'0123456789')
    backing_write.close()
    assert f.tell() == 0
    assert f.read(1) == b'0'
    assert f.tell() == 1
    assert f.read() == b'123456789'
    assert f.tell() == 10
    backing_read.close()
