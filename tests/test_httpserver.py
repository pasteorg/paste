import email
import io

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
    assert f.read() == b'012345678'
    assert f.read() == b''
