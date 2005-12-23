# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
WSGI HTTP Server

This is a minimalistic WSGI server using Python's built-in BaseHTTPServer;
if pyOpenSSL is installed, it also provides SSL capabilities.
"""

# @@: add in protection against HTTP/1.0 clients who claim to
#     be 1.1 but do not send a Content-Length

# @@: add support for chunked encoding, this is not a 1.1 server
#     till this is completed.


import BaseHTTPServer, SocketServer
import urlparse, sys, socket

__all__ = ['WSGIHandlerMixin','WSGIServer','WSGIHandler', 'serve']
__version__ = "0.2"

class ContinueHook(object):
    """
    When a client request includes a 'Expect: 100-continue' header, then
    it is the responsibility of the server to send 100 Continue when it
    is ready for the content body.  This allows authentication, access
    levels, and other exceptions to be detected *before* bandwith is
    spent on the request body.

    This is a rfile wrapper that implements this functionality by
    sending 100 Continue to the client immediately after the user
    requests the content via a read() operation on the rfile stream.
    After this response is sent, it becomes a pass-through object.
    """

    def __init__(self, rfile, write):
        self._ContinueFile_rfile = rfile
        self._ContinueFile_write = write
        for attr in ('close','closed','fileno','flush',
                     'mode','bufsize','softspace'):
            if hasattr(rfile,attr):
                setattr(self,attr,getattr(rfile,attr))
        for attr in ('read','readline','readlines'):
            if hasattr(rfile,attr):
                setattr(self,attr,getattr(self,'_ContinueFile_' + attr))

    def _ContinueFile_send(self):
        self._ContinueFile_write("HTTP/1.1 100 Continue\r\n\r\n")
        rfile = self._ContinueFile_rfile
        for attr in ('read','readline','readlines'):
            if hasattr(rfile,attr):
                setattr(self,attr,getattr(rfile,attr))

    def _ContinueFile_read(self, size=-1):
        self._ContinueFile_send()
        return self._ContinueFile_rfile.readline(size)

    def _ContinueFile_readline(self, size=-1):
        self._ContinueFile_send()
        return self._ContinueFile_rfile.readline(size)

    def _ContinueFile_readlines(self, sizehint=0):
        self._ContinueFile_send()
        return self._ContinueFile_rfile.readlines(sizehint)


class WSGIHandlerMixin:
    """
    WSGI mix-in for HTTPRequestHandler

    This class is a mix-in to provide WSGI functionality to any
    HTTPRequestHandler derivative (as provided in Python's BaseHTTPServer).
    This assumes a ``wsgi_application`` handler on ``self.server``.
    """

    def version_string(self):
        """ behavior that BaseHTTPServer should have had """
        if not self.sys_version:
            return self.server_version
        else:
            return self.server_version + ' ' + self.sys_version

    def wsgi_write_chunk(self, chunk):
        """
        Write a chunk of the output stream; send headers if they
        have not already been sent.
        """
        if not self.wsgi_headers_sent:
            self.wsgi_headers_sent = True
            (status, headers) = self.wsgi_curr_headers
            code, message = status.split(" ",1)
            self.send_response(int(code),message)
            #
            # HTTP/1.1 compliance; either send Content-Length or
            # signal that the connection is being closed.
            #
            send_close = True
            for (k,v) in  headers:
                k = k.lower()
                if 'content-length' == k:
                    send_close = False
                if 'connection' == k:
                    if 'close' == v.lower():
                        self.close_connection = 1
                        send_close = False
                self.send_header(k,v)
            if send_close:
                self.close_connection = 1
                self.send_header('Connection','close')

            self.end_headers()
        self.wfile.write(chunk)

    def wsgi_start_response(self,status,response_headers,exc_info=None):
        if exc_info:
            try:
                if self.wsgi_headers_sent:
                    raise exc_info[0], exc_info[1], exc_info[2]
                else:
                    # In this case, we're going to assume that the
                    # higher-level code is currently handling the
                    # issue and returning a resonable response.
                    # self.log_error(repr(exc_info))
                    pass
            finally:
                exc_info = None
        elif self.wsgi_curr_headers:
            assert 0, "Attempt to set headers a second time w/o an exc_info"
        self.wsgi_curr_headers = (status, response_headers)
        return self.wsgi_write_chunk

    def wsgi_setup(self, environ=None):
        """
        Setup the member variables used by this WSGI mixin, including
        the ``environ`` and status member variables.

        After the basic environment is created; the optional ``environ``
        argument can be used to override any settings.
        """

        (_,_,path,query,fragment) = urlparse.urlsplit(self.path)
        (server_name, server_port) = self.server.server_address

        rfile = self.rfile
        if 'HTTP/1.1' == self.protocol_version and \
                '100-continue' == self.headers.get('Expect',''):
            rfile = ContinueHook(rfile, self.wfile.write)

        self.wsgi_environ = {
                'wsgi.version': (1,0)
               ,'wsgi.url_scheme': 'http'
               ,'wsgi.input': rfile
               ,'wsgi.errors': sys.stderr
               ,'wsgi.multithread': True
               ,'wsgi.multiprocess': False
               ,'wsgi.run_once': True
               # CGI variables required by PEP-333
               ,'REQUEST_METHOD': self.command
               ,'SCRIPT_NAME': '' # application is root of server
               ,'PATH_INFO': path
               ,'QUERY_STRING': query
               ,'CONTENT_TYPE': self.headers.get('Content-Type', '')
               ,'CONTENT_LENGTH': self.headers.get('Content-Length', '')
               ,'SERVER_NAME': server_name
               ,'SERVER_PORT': str(server_port)
               ,'SERVER_PROTOCOL': self.request_version
               # CGI not required by PEP-333
               ,'REMOTE_ADDR': self.client_address[0]
               ,'REMOTE_HOST': self.address_string()
               }

        for k,v in self.headers.items():
            self.wsgi_environ['HTTP_%s' % k.replace ('-', '_').upper()] = v

        if hasattr(self.connection,'get_context'):
            self.wsgi_environ['wsgi.url_scheme'] = 'https'
            # @@: extract other SSL parameters from pyOpenSSL at...
            # http://www.modssl.org/docs/2.8/ssl_reference.html#ToC25

        if environ:
            assert isinstance(environ,dict)
            self.wsgi_environ.update(environ)
            if 'on' == environ.get('HTTPS'):
                self.wsgi_environ['wsgi.url_scheme'] = 'https'

        self.wsgi_curr_headers = None
        self.wsgi_headers_sent = False

    def wsgi_execute(self, environ=None):
        """
        Invoke the server's ``wsgi_application``.
        """

        self.wsgi_setup(environ)

        try:
            result = self.server.wsgi_application(self.wsgi_environ,
                                                  self.wsgi_start_response)
            try:
                for chunk in result:
                    self.wsgi_write_chunk(chunk)
            finally:
                if hasattr(result,'close'):
                    result.close()
        except socket.error:
            # @@: what do we do with this exception?  Sending a 500
            # isn't smart in this case, which is why it is being singled
            # out here.  Yet, SocketServer@218 just ignores this sort of
            # error... is this acceptable?  Let's just punt.
            raise
        except:
            if not self.wsgi_headers_sent:
                self.wsgi_curr_headers = ('500 Internal Server Error',
                                        [('Content-type', 'text/plain')])
                self.wsgi_write_chunk("Internal Server Error\n")
            raise

class WSGIHandler(WSGIHandlerMixin, BaseHTTPServer.BaseHTTPRequestHandler):
    """
    A WSGI handler that overrides POST, GET and HEAD to delegate
    requests to the server's ``wsgi_application``.
    """
    do_POST = do_GET = do_HEAD = do_DELETE = do_PUT = do_TRACE = \
        WSGIHandlerMixin.wsgi_execute

#
# SSL Functionality
#
# This implementation was motivated by Sebastien Martini's SSL example
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/442473
#
try:
    from OpenSSL import SSL
except ImportError:
    # Do not require pyOpenSSL to be installed, but disable SSL
    # functionality in that case.
    SSL = None
    class SecureHTTPServer(BaseHTTPServer.HTTPServer):
        def __init__(self, server_address, RequestHandlerClass,
                     ssl_context=None):
            assert not ssl_context, "pyOpenSSL not installed"
            BaseHTTPServer.HTTPServer.__init__(self, server_address,
                                               RequestHandlerClass)
else:

    class _ConnFixer(object):
        """ wraps a socket connection so it implements makefile """
        def __init__(self, conn):
            self.__conn = conn
        def makefile(self, mode, bufsize):
            return socket._fileobject(self.__conn, mode, bufsize)
        def __getattr__(self, attrib):
            return getattr(self.__conn, attrib)

    class SecureHTTPServer(BaseHTTPServer.HTTPServer):
        """
        Provides SSL server functionality on top of the BaseHTTPServer
        by overriding _private_ members of Python's standard
        distribution. The interface for this instance only changes by
        adding a an optional ssl_context attribute to the constructor:

              cntx = SSL.Context(SSL.SSLv23_METHOD)
              cntx.use_privatekey_file("host.pem")
              cntx.use_certificate_file("host.pem")

        The certificates can be generated with openssl as follows:

            $ openssl genrsa 1024 > host.key
            $ chmod 400 host.key
            $ openssl req -new -x509 -nodes -sha1 -days 365  \
                          -key host.key > host.cert
            $ cat host.cert host.key > host.pem
            $ chmod 400 host.pem

        """

        def __init__(self, server_address, RequestHandlerClass,
                     ssl_context=None):
            # This overrides the implementation of __init__ in python's
            # SocketServer.TCPServer (which BaseHTTPServer.HTTPServer
            # does not override, thankfully).
            BaseHTTPServer.HTTPServer.__init__(self, server_address,
                                               RequestHandlerClass)
            self.socket = socket.socket(self.address_family,
                                        self.socket_type)
            self.ssl_context = ssl_context
            if ssl_context:
                self.socket = SSL.Connection(ssl_context, self.socket)
            self.server_bind()
            self.server_activate()

        def get_request(self):
            # The default SSL request object does not seem to have a
            # ``makefile(mode, bufsize)`` method as expected by
            # Socketserver.StreamRequestHandler.
            (conn,info) = self.socket.accept()
            if self.ssl_context:
                conn = _ConnFixer(conn)
            return (conn,info)

class WSGIServer(SocketServer.ThreadingMixIn, SecureHTTPServer):
    server_version = 'WSGIServer/' + __version__
    def __init__(self, wsgi_application, server_address,
                 RequestHandlerClass=None, ssl_context=None):
        SecureHTTPServer.__init__(self, server_address,
                                  RequestHandlerClass, ssl_context)
        self.wsgi_application = wsgi_application

def serve(application, host=None, port=None, handler=None, ssl_pem=None,
          server_version=None, protocol_version=None):

    ssl_context = None
    if ssl_pem:
        assert SSL, "pyOpenSSL is not installed"
        port = port or 4443
        ssl_context = SSL.Context(SSL.SSLv23_METHOD)
        ssl_context.use_privatekey_file(ssl_pem)
        ssl_context.use_certificate_file(ssl_pem)

    server_address = (host or "127.0.0.1", port or 8080)

    if not handler:
        handler = WSGIHandler
    if server_version:
        handler.server_version = server_version
        handler.sys_version = None

    if protocol_version:
        handler.protocol_version = protocol_version

    server = WSGIServer(application, server_address, handler, ssl_context)
    print "serving on %s:%s" % server.server_address
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        # allow CTRL+C to shutdown
        pass
    return server

if __name__ == '__main__':
    # serve exactly 3 requests and then stop, use an external
    # program like wget or curl to submit these 3 requests.
    from paste.wsgilib import dump_environ
    #serve(dump_environ, ssl_pem="test.pem")
    serve(dump_environ, server_version="Wombles/1.0",
          protocol_version="HTTP/1.1")

