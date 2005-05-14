"""
cgi WSGI server
===============

Usage
-----

The CGI script is the configuration and glue for this server.
Typically you will write a CGI script like::

    #!/usr/bin/env python
    from paste.cgiserver import run_with_cgi
    # Assuming app is your WSGI application object...
    from myapplication import app
    run_with_cgi(app)

"""

import os, sys

def run_with_cgi(application,
                 use_cgitb=True,
                 redirect_stdout=False):
    stdout = sys.stdout

    if use_cgitb:
        import cgitb
        cgitb.enable()
    
    environ = dict(os.environ)
    environ['wsgi.input']        = sys.stdin
    environ['wsgi.errors']       = sys.stderr
    environ['wsgi.version']      = (1, 0)
    environ['wsgi.multithread']  = False
    environ['wsgi.multiprocess'] = True
    environ['wsgi.run_once']     = True

    if os.environ.get('HTTPS', 'off').lower() in ('on', '1'):
        environ['wsgi.url_scheme'] = 'https'
    else:
        environ['wsgi.url_scheme'] = 'http'

    if redirect_stdout:
        sys.stdout = sys.stderr

    headers_set = []
    headers_sent = []
    result = None

    def write(data):
        assert headers_set, "write() before start_response()"

        if not headers_sent:
             # Before the first output, send the stored headers
             status, response_headers = headers_sent[:] = headers_set

             # See if Content-Length is given.
             found = False
             for name, value in response_headers:
                 if name.lower() == 'content-length':
                     found = True
                     break

             # If not given, try to deduce it if the iterator implements
             # __len__ and is of length 1. (data will be result[0] in this
             # case.)
             if not found and result is not None:
                 try:
                     if len(result) == 1:
                         response_headers.append(('Content-Length',
                                                  str(len(data))))
                 except:
                     pass

             stdout.write('Status: %s\r\n' % status)
             for header in response_headers:
                 stdout.write('%s: %s\r\n' % header)
             stdout.write('\r\n')

        stdout.write(data)
        stdout.flush()

    def start_response(status, response_headers, exc_info=None):
        if exc_info:
            try:
                if headers_sent:
                    # Re-raise original exception if headers sent
                    raise exc_info[0], exc_info[1], exc_info[2]
            finally:
                exc_info = None     # avoid dangling circular ref
        else:
            assert not headers_set, "Headers already set!"
            
        headers_set[:] = [status, response_headers]
        return write

    result = application(environ, start_response)
    try:
        for data in result:
            if data:    # don't send headers until body appears
                write(data)
        if not headers_sent:
            write('')   # send headers now if body was empty
    finally:
        if hasattr(result, 'close'):
            result.close()

if __name__ == '__main__':
    def myapp(environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return ['Hello World!\n']

    run_with_cgi(myapp)
