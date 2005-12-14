# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
WSGI HTTP Server

This is a minimalistic WSGI server using Python's built-in BaseHTTPServer;
if pyOpenSSL is installed, it also provides SSL capabilities.
"""

import BaseHTTPServer, SocketServer
import urlparse, sys, time, socket

try:
    from paste.httpexceptions import HTTPServerError
except ImportError:
    # so we can run this module independent of paste
    HTTPServerError = RuntimeError

__all__ = ['WSGIHandlerMixin','WSGIServer','WSGIHandler', 'serve']
__version__ = "0.2"


class WSGIHandlerMixin:
    """
    WSGI mix-in for HTTPRequestHandler

    This class is a mix-in to provide WSGI functionality to any
    HTTPRequestHandler derivative (as provided in Python's BaseHTTPServer).
    This assumes a ``wsgi_application`` handler on ``self.server``.
    """
    
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
            for (k,v) in  headers:
                self.send_header(k,v)
            self.end_headers()
        self.wfile.write(chunk)
    
    def wsgi_start_response(self,status,response_headers,exc_info=None):
        if exc_info:
            try:
                if self.wsgi_headers_sent:
                    raise exc_info[0], exc_info[1], exc_info[2]
                else:
                    self.log_error(exc_info)
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

        self.wsgi_environ = { 
                'wsgi.version': (1,0)
               ,'wsgi.url_scheme': 'http'
               ,'wsgi.input': self.rfile
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
        except socket.error, exce:
            # do not stop the server on a network error; is this needed?
            self.log_error("Network Error: %s", exce)
            return
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
    do_POST = do_GET = do_HEAD = WSGIHandlerMixin.wsgi_execute


class WSGIServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    def __init__ (self, application, host=None, port=None, handler=None):
        server_address = (host or "127.0.0.1", port or 8080)
        BaseHTTPServer.HTTPServer.__init__ (self,server_address,
                                            handler or WSGIHandler)
        self.wsgi_application = application

def serve(application, host=None, port=None, handler=None):
    server = WSGIServer(application,host,port,handler)
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
    import os
    from paste.wsgilib import dump_environ
    serve(dump_environ)
