# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
WSGI Base Server

Very minimalistic WSGI server using Python's built-in BaseHTTPServer; it
is intended for use in the regression tests suites using a separate
thread for urlib2 requests.  This is probably not a good thing to use in
a production setting; the focus here is transparency, not robustness.
"""

import BaseHTTPServer, SocketServer
import urlparse, sys, time, socket
try:
    from paste.httpexceptions import HTTPServerError
except ImportError:
    # so we can run this module independent of paste
    HTTPServerError = RuntimeError

__all__ = ['WSGIServer','WSGIHandler', 'serve']

class WSGIHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version = 'WSGIHandler/0.1'
    protocol_version = 'HTTP/1.0'

    def write_chunk(self, chunk):
        if not self.headers_sent:
            self.headers_sent = True
            (status, headers) = self.curr_headers
            code, message = status.split(" ",1)
            self.send_response(int(code),message)
            for (k,v) in  headers:
                self.send_header(k,v)
            self.end_headers()
        self.wfile.write(chunk)

    def start_response(self,status,response_headers,exc_info=None):
        if exc_info:
            try:
                if self.headers_sent:
                    raise exc_info[0], exc_info[1], exc_info[2]
                else:
                    self.log_error(exc_info)
            finally:
                exc_info = None
        elif self.curr_headers:
            assert 0, "Attempt to set headers a second time w/o an exc_info"
        self.curr_headers = (status, response_headers)
        return self.write_chunk

    def run_application(self, environ):
        try:
            result = self.server.application(environ, self.start_response)
            try:
                for chunk in result:
                    self.write_chunk(chunk)
            finally:
                if hasattr(result,'close'):
                    result.close()
        except socket.error, exce:
            self.log_error("Network Error: %s", exce)
            return
        except:
            if not self.headers_sent:
                self.curr_headers = ('500 Internal Server Error',
                                     [('Content-type', 'text/plain')])
                self.write_chunk("Internal Server Error\n")
            raise

    def do_GET(self):
        (_,_,path,query,fragment) = urlparse.urlsplit(self.path)
        (server_name, server_port) = self.server.server_address
        env = { 'wsgi.version': (1,0)
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
               ,'REQUEST_SCHEME': 'http'
               ,'SERVER_NAME': server_name
               ,'SERVER_PORT': str(server_port)
               ,'SERVER_PROTOCOL': self.request_version
               # CGI not required by PEP-333
               ,'REMOTE_ADDR': self.client_address[0]
               ,'REMOTE_HOST': self.address_string()
               }
        for k,v in self.headers.items():
            env['HTTP_%s' % k.replace ('-', '_').upper()] = v
        self.curr_headers = None
        self.headers_sent = False
        self.run_application(env)
    
    do_POST = do_GET

class WSGIServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    def __init__ (self, application, host=None, port=None, handler=None):
        server_address = (host or "127.0.0.1", port or 8080)
        BaseHTTPServer.HTTPServer.__init__ (self,server_address,
                                            handler or WSGIHandler)
        self.application = application

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
