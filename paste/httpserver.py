# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
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

import atexit
import socket, sys, threading, urlparse, Queue, urllib
import posixpath
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
from paste.util import converters

__all__ = ['WSGIHandlerMixin', 'WSGIServer', 'WSGIHandler', 'serve']
__version__ = "0.5"

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
        for attr in ('close', 'closed', 'fileno', 'flush',
                     'mode', 'bufsize', 'softspace'):
            if hasattr(rfile, attr):
                setattr(self, attr, getattr(rfile, attr))
        for attr in ('read', 'readline', 'readlines'):
            if hasattr(rfile, attr):
                setattr(self, attr, getattr(self, '_ContinueFile_' + attr))

    def _ContinueFile_send(self):
        self._ContinueFile_write("HTTP/1.1 100 Continue\r\n\r\n")
        rfile = self._ContinueFile_rfile
        for attr in ('read', 'readline', 'readlines'):
            if hasattr(rfile, attr):
                setattr(self, attr, getattr(rfile, attr))

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

    def log_request(self, *args, **kwargs):
        """ disable success request logging

        Logging transactions should not be part of a WSGI server,
        if you want logging; look at paste.translogger
        """
        pass

    def log_message(self, *args, **kwargs):
        """ disable error message logging

        Logging transactions should not be part of a WSGI server,
        if you want logging; look at paste.translogger
        """
        pass

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
            code, message = status.split(" ", 1)
            self.send_response(int(code), message)
            #
            # HTTP/1.1 compliance; either send Content-Length or
            # signal that the connection is being closed.
            #
            send_close = True
            for (k, v) in  headers:
                k = k.lower()
                if 'content-length' == k:
                    send_close = False
                if 'connection' == k:
                    if 'close' == v.lower():
                        self.close_connection = 1
                        send_close = False
                self.send_header(k, v)
            if send_close:
                self.close_connection = 1
                self.send_header('Connection', 'close')

            self.end_headers()
        self.wfile.write(chunk)

    def wsgi_start_response(self, status, response_headers, exc_info=None):
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

        (_, _, path, query, fragment) = urlparse.urlsplit(self.path)
        path = urllib.unquote(path)
        endslash = path.endswith('/')
        path = posixpath.normpath(path)
        if endslash and path != '/':
            # Put the slash back...
            path += '/'
        (server_name, server_port) = self.server.server_address

        rfile = self.rfile
        if 'HTTP/1.1' == self.protocol_version and \
                '100-continue' == self.headers.get('Expect','').lower():
            rfile = ContinueHook(rfile, self.wfile.write)

        self.wsgi_environ = {
                'wsgi.version': (1,0)
               ,'wsgi.url_scheme': 'http'
               ,'wsgi.input': rfile
               ,'wsgi.errors': sys.stderr
               ,'wsgi.multithread': True
               ,'wsgi.multiprocess': False
               ,'wsgi.run_once': False
               # CGI variables required by PEP-333
               ,'REQUEST_METHOD': self.command
               ,'SCRIPT_NAME': '' # application is root of server
               ,'PATH_INFO': path
               ,'QUERY_STRING': query
               ,'CONTENT_TYPE': self.headers.get('Content-Type', '')
               ,'CONTENT_LENGTH': self.headers.get('Content-Length', '0')
               ,'SERVER_NAME': server_name
               ,'SERVER_PORT': str(server_port)
               ,'SERVER_PROTOCOL': self.request_version
               # CGI not required by PEP-333
               ,'REMOTE_ADDR': self.client_address[0]
               ,'REMOTE_HOST': self.address_string()
               }
        
        for k, v in self.headers.items():
            key = 'HTTP_' + k.replace("-","_").upper()
            if key in ('HTTP_CONTENT_TYPE','HTTP_CONTENT_LENGTH'):
                continue
            self.wsgi_environ[key] = ','.join(self.headers.getheaders(k))
        
        if hasattr(self.connection,'get_context'):
            self.wsgi_environ['wsgi.url_scheme'] = 'https'
            # @@: extract other SSL parameters from pyOpenSSL at...
            # http://www.modssl.org/docs/2.8/ssl_reference.html#ToC25

        if environ:
            assert isinstance(environ, dict)
            self.wsgi_environ.update(environ)
            if 'on' == environ.get('HTTPS'):
                self.wsgi_environ['wsgi.url_scheme'] = 'https'

        self.wsgi_curr_headers = None
        self.wsgi_headers_sent = False

    def wsgi_connection_drop(self, exce, environ=None):
        """
        Override this if you're interested in socket exceptions, such
        as when the user clicks 'Cancel' during a file download.
        """
        pass

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
                if not self.wsgi_headers_sent:
                    self.wsgi_write_chunk('')
            finally:
                if hasattr(result,'close'):
                    result.close()
        except socket.error, exce:
            self.wsgi_connection_drop(exce, environ)
            return
        except:
            if not self.wsgi_headers_sent:
                self.wsgi_curr_headers = ('500 Internal Server Error',
                                        [('Content-type', 'text/plain')])
                self.wsgi_write_chunk("Internal Server Error\n")
            raise

#
# SSL Functionality
#
# This implementation was motivated by Sebastien Martini's SSL example
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/442473
#
try:
    from OpenSSL import SSL
    SocketErrors = (socket.error, SSL.ZeroReturnError, SSL.SysCallError)
except ImportError:
    # Do not require pyOpenSSL to be installed, but disable SSL
    # functionality in that case.
    SSL = None
    SocketErrors = (socket.error,)
    class SecureHTTPServer(HTTPServer):
        def __init__(self, server_address, RequestHandlerClass,
                     ssl_context=None):
            assert not ssl_context, "pyOpenSSL not installed"
            HTTPServer.__init__(self, server_address, RequestHandlerClass)
else:

    class _ConnFixer(object):
        """ wraps a socket connection so it implements makefile """
        def __init__(self, conn):
            self.__conn = conn
        def makefile(self, mode, bufsize):
            return socket._fileobject(self.__conn, mode, bufsize)
        def __getattr__(self, attrib):
            return getattr(self.__conn, attrib)

    class SecureHTTPServer(HTTPServer):
        """
        Provides SSL server functionality on top of the BaseHTTPServer
        by overriding _private_ members of Python's standard
        distribution. The interface for this instance only changes by
        adding a an optional ssl_context attribute to the constructor:

              cntx = SSL.Context(SSL.SSLv23_METHOD)
              cntx.use_privatekey_file("host.pem")
              cntx.use_certificate_file("host.pem")

        """

        def __init__(self, server_address, RequestHandlerClass,
                     ssl_context=None):
            # This overrides the implementation of __init__ in python's
            # SocketServer.TCPServer (which BaseHTTPServer.HTTPServer
            # does not override, thankfully).
            HTTPServer.__init__(self, server_address, RequestHandlerClass)
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
            (conn, info) = self.socket.accept()
            if self.ssl_context:
                conn = _ConnFixer(conn)
            return (conn, info)

    def _auto_ssl_context():
        import OpenSSL, time, random
        pkey = OpenSSL.crypto.PKey()
        pkey.generate_key(OpenSSL.crypto.TYPE_RSA, 768)

        cert = OpenSSL.crypto.X509()

        cert.set_serial_number(random.randint(0, sys.maxint))
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(60 * 60 * 24 * 365)
        cert.get_subject().CN = '*'
        cert.get_subject().O = 'Dummy Certificate'
        cert.get_issuer().CN = 'Untrusted Authority'
        cert.get_issuer().O = 'Self-Signed'
        cert.set_pubkey(pkey)
        cert.sign(pkey, 'md5')

        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_privatekey(pkey)
        ctx.use_certificate(cert)

        return ctx

class WSGIHandler(WSGIHandlerMixin, BaseHTTPRequestHandler):
    """
    A WSGI handler that overrides POST, GET and HEAD to delegate
    requests to the server's ``wsgi_application``.
    """
    server_version = 'PasteWSGIServer/' + __version__
    do_POST = do_GET = do_HEAD = do_DELETE = do_PUT = do_TRACE = \
        WSGIHandlerMixin.wsgi_execute

    def handle(self):
        # don't bother logging disconnects while handling a request
        try:
            BaseHTTPRequestHandler.handle(self)
        except SocketErrors, exce:
            self.wsgi_connection_drop(exce)

class ThreadPool(object):
    """
    Generic thread pool with a queue of callables to consume.
    """
    SHUTDOWN = object()

    def __init__(self, nworkers, name="ThreadPool", daemon=False):
        """
        Create thread pool with `nworkers` worker threads.
        """
        self.nworkers = nworkers
        self.name = name
        self.queue = Queue.Queue()
        self.workers = []
        for i in range(self.nworkers):
            worker = threading.Thread(target=self.worker_thread_callback,
                                      name=("%s worker %d" % (self.name, i)))
            worker.setDaemon(daemon)
            worker.start()
            self.workers.append(worker)

        if not daemon:
            atexit.register(self.shutdown)

    def worker_thread_callback(self):
        """
        Worker thread should call this method to get and process queued
        callables.
        """
        while True:
            runnable = self.queue.get()
            if runnable is ThreadPool.SHUTDOWN:
                return
            else:
                runnable()

    def shutdown(self):
        """
        Shutdown the queue (after finishing any pending requests).
        """
        # Add a shutdown request for every worker
        for i in range(self.nworkers):
            self.queue.put(ThreadPool.SHUTDOWN)
        # Wait for each thread to terminate
        for worker in self.workers:
            worker.join()

class ThreadPoolMixIn(object):
    """
    Mix-in class to process requests from a thread pool
    """
    def __init__(self, nworkers, daemon=False):
        # Create and start the workers
        self.running = True
        assert nworkers > 0, "ThreadPoolMixin servers must have at least one worker"
        self.thread_pool = ThreadPool(nworkers,
            "ThreadPoolMixin HTTP server on %s:%d"
                % (self.server_name, self.server_port), daemon)

    def process_request(self, request, client_address):
        """
        Queue the request to be processed by on of the thread pool threads
        """
        # This sets the socket to blocking mode (and no timeout) since it
        # may take the thread pool a little while to get back to it. (This
        # is the default but since we set a timeout on the parent socket so
        # that we can trap interrupts we need to restore this,.)
        request.setblocking(1)
        # Queue processing of the request
        self.thread_pool.queue.put(
            lambda: self.process_request_in_thread(request, client_address))

    def process_request_in_thread(self, request, client_address):
        """
        The worker thread should call back here to do the rest of the
        request processing. Error handling normaller done in 'handle_request'
        must be done here.
        """
        try:
            self.finish_request(request, client_address)
            self.close_request(request)
        except:
            self.handle_error(request, client_address)
            self.close_request(request)

    def serve_forever(self):
        """
        Overrides `serve_forever` to shut the threadpool down cleanly.
        """
        try:
            while self.running:
                try:
                    self.handle_request()
                except socket.timeout:
                    # Timeout is expected, gives interrupts a chance to
                    # propogate, just keep handling
                    pass
        finally:
            self.thread_pool.shutdown()

    def server_activate(self):
        """
        Overrides server_activate to set timeout on our listener socket.
        """
        # We set the timeout here so that we can trap interrupts on windows
        self.socket.settimeout(1)
        self.socket.listen(self.request_queue_size)

    def server_close(self):
        """
        Finish pending requests and shutdown the server.
        """
        self.running = False
        self.socket.close()
        self.thread_pool.shutdown()

class WSGIServerBase(SecureHTTPServer):
    def __init__(self, wsgi_application, server_address,
                 RequestHandlerClass=None, ssl_context=None):
        SecureHTTPServer.__init__(self, server_address,
                                  RequestHandlerClass, ssl_context)
        self.wsgi_application = wsgi_application
        self.wsgi_socket_timeout = None

    def get_request(self):
        # If there is a socket_timeout, set it on the accepted
        (conn,info) = SecureHTTPServer.get_request(self)
        if self.wsgi_socket_timeout:
            conn.settimeout(self.wsgi_socket_timeout)
        return (conn, info)

class WSGIServer(ThreadingMixIn, WSGIServerBase):
    daemon_threads = False

class WSGIThreadPoolServer(ThreadPoolMixIn, WSGIServerBase):
    def __init__(self, wsgi_application, server_address,
                 RequestHandlerClass=None, ssl_context=None,
                 nworkers=10, daemon_threads=False):
        WSGIServerBase.__init__(self, wsgi_application, server_address,
                                RequestHandlerClass, ssl_context)
        ThreadPoolMixIn.__init__(self, nworkers, daemon_threads)

def serve(application, host=None, port=None, handler=None, ssl_pem=None,
          ssl_context=None, server_version=None, protocol_version=None,
          start_loop=True, daemon_threads=None, socket_timeout=None,
          use_threadpool=True, threadpool_workers=10):
    """
    Serves your ``application`` over HTTP(S) via WSGI interface

    ``host``

        This is the ipaddress to bind to (or a hostname if your
        nameserver is properly configured).  This defaults to
        127.0.0.1, which is not a public interface.

    ``port``

        The port to run on, defaults to 8080 for HTTP, or 4443 for
        HTTPS. This can be a string or an integer value.

    ``handler``

        This is the HTTP request handler to use, it defaults to
        ``WSGIHandler`` in this module.

    ``ssl_pem``

        This an optional SSL certificate file (via OpenSSL). You can
        supply ``*`` and a development-only certificate will be
        created for you, or you can generate a self-signed test PEM
        certificate file as follows:

            $ openssl genrsa 1024 > host.key
            $ chmod 400 host.key
            $ openssl req -new -x509 -nodes -sha1 -days 365  \
                          -key host.key > host.cert
            $ cat host.cert host.key > host.pem
            $ chmod 400 host.pem

    ``ssl_context``

        This an optional SSL context object for the server.  A SSL
        context will be automatically constructed for you if you supply
        ``ssl_pem``.  Supply this to use a context of your own
        construction.

    ``server_version``

        The version of the server as reported in HTTP response line. This
        defaults to something like "PasteWSGIServer/0.5".  Many servers
        hide their code-base identity with a name like 'Amnesiac/1.0'

    ``protocol_version``

        This sets the protocol used by the server, by default
        ``HTTP/1.0``. There is some support for ``HTTP/1.1``, which
        defaults to nicer keep-alive connections.  This server supports
        ``100 Continue``, but does not yet support HTTP/1.1 Chunked
        Encoding. Hence, if you use HTTP/1.1, you're somewhat in error
        since chunked coding is a mandatory requirement of a HTTP/1.1
        server.  If you specify HTTP/1.1, every response *must* have a
        ``Content-Length`` and you must be careful not to read past the
        end of the socket.

    ``start_loop``

        This specifies if the server loop (aka ``server.serve_forever()``)
        should be called; it defaults to ``True``.

    ``daemon_threads``

        This flag specifies if when your webserver terminates all
        in-progress client connections should be droppped.  It defaults
        to ``False``.   You might want to set this to ``True`` if you
        are using ``HTTP/1.1`` and don't set a ``socket_timeout``.

    ``socket_timeout``

        This specifies the maximum amount of time that a connection to a
        given client will be kept open.  At this time, it is a rude
        disconnect, but at a later time it might follow the RFC a bit
        more closely.

    ``use_threadpool``

        Server requests from a pool of worker threads (``threadpool_workers``)
        rather than creating a new thread for each request. This can
        substantially reduce latency since there is a high cost associated
        with thread creation.

    ``threadpool_workers``

        Number of worker threads to create when ``use_threadpool`` is true. This
        can be a string or an integer value.
    """
    is_ssl = False
    if ssl_pem or ssl_context:
        assert SSL, "pyOpenSSL is not installed"
        is_ssl = True
        port = int(port or 4443)
        if not ssl_context:
            if ssl_pem == '*':
                ssl_context = _auto_ssl_context()
            else:
                ssl_context = SSL.Context(SSL.SSLv23_METHOD)
                ssl_context.use_privatekey_file(ssl_pem)
                ssl_context.use_certificate_file(ssl_pem)

    host = host or '127.0.0.1'
    if not port:
        if ':' in host:
            host, port = host.split(':', 1)
        else:
            port = 8080
    server_address = (host, int(port))

    if not handler:
        handler = WSGIHandler
    if server_version:
        handler.server_version = server_version
        handler.sys_version = None
    if protocol_version:
        assert protocol_version in ('HTTP/0.9', 'HTTP/1.0', 'HTTP/1.1')
        handler.protocol_version = protocol_version


    if converters.asbool(use_threadpool):
        server = WSGIThreadPoolServer(application, server_address, handler,
                                      ssl_context, int(threadpool_workers),
                                      daemon_threads)
    else:
        server = WSGIServer(application, server_address, handler, ssl_context)
        if daemon_threads:
            server.daemon_threads = daemon_threads

    if socket_timeout:
        server.wsgi_socket_timeout = int(socket_timeout)

    if converters.asbool(start_loop):
        protocol = is_ssl and 'https' or 'http'
        host, port = server.server_address
        if host == '0.0.0.0':
            print 'serving on 0.0.0.0:%s view at %s://127.0.0.1:%s' % \
                (port, protocol, port)
        else:
            print "serving on %s://%s:%s" % (protocol, host, port)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            # allow CTRL+C to shutdown
            pass
    return server

# For paste.deploy server instantiation (egg:Paste#http)
# Note: this gets a separate function because it has to expect string
# arguments (though that's not much of an issue yet, ever?)
def server_runner(wsgi_app, global_conf, *args, **kwargs):
    serve(wsgi_app, *args, **kwargs)

server_runner.__doc__ = serve.__doc__

if __name__ == '__main__':
    # serve exactly 3 requests and then stop, use an external
    # program like wget or curl to submit these 3 requests.
    from paste.wsgilib import dump_environ
    #serve(dump_environ, ssl_pem="test.pem")
    serve(dump_environ, server_version="Wombles/1.0",
          protocol_version="HTTP/1.1", port="8888")
