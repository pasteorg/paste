"""
A WSGI middleware that allows for recursive and forwarded calls.
All these calls go to the same 'application', but presumably that
application acts differently with different URLs.  The forwarded
URLs must be relative to this container.

The forwarder is available through
``environ['wsgikit.recursive.forward'](path, extra_environ=None)``,
the second argument is a dictionary of values to be added to the
request, overwriting any keys.  The forward will call start_response;
thus you must *not* call it after you have sent any output to the
server.  Also, it will return an iterator that must be returned up the
stack.  You may need to use exceptions to guarantee that this iterator
will be passed back through the application.

The includer is available through
``environ['wsgikit.recursive.include'](path, extra_environ=None)``.
It is like forwarder, except it completes the request and returns a
response object.  The response object has three public attributes:
status, headers, and body.  The status is a string, headers is a list
of (header_name, header_value) tuples, and the body is a string.
"""

from cStringIO import StringIO

class RecursiveMiddleware(object):

    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        environ['wsgikit.recursive.forward'] = Forwarder(
            self.application, environ, start_response)
        environ['wsgikit.recursive.include'] = Includer(
            self.application, environ, start_response)
        return self.application(environ, start_response)

class Recursive(object):

    def __init__(self, application, environ, start_response):
        self.application = application
        self.original_environ = environ.copy()
        self.previous_environ = environ
        self.start_response = start_response

    def __call__(self, path, new_environ=None):
        environ = self.original_environ.copy()
        if new_environ:
            environ.update(new_environ)
        environ['wsgikit.recursive.previous_environ'] = self.previous_environ
        base_path = self.original_environ.get('SCRIPT_NAME')
        if path.startswith('/'):
            assert path.startswith(base_path), "You can only forward requests to resources under the path %r (not %r)" % (base_path, path)
            path = path[len(base_path)+1:]
        assert not path.startswith('/')
        path_info = '/' + path
        environ['PATH_INFO'] = path_info
        return self.activate(environ)

class Forwarder(Recursive):

    def activate(self, environ):
        environ['wsgi.errors'].write('Forwarding to %r\n' % (environ['SCRIPT_NAME'] + environ['PATH_INFO']))
        return self.application(environ, self.start_response)

class Includer(Recursive):
    
    def activate(self, environ):
        environ['wsgi.errors'].write('Including %r\n' % (environ['SCRIPT_NAME'] + environ['PATH_INFO']))
        response = IncludedResponse
        def start_response(status, headers):
            response.status = status
            response.headers = headers
            return response.write
        app_iter = self.application(environ, start_response)
        try:
            for s in app_iter:
                response.write(s)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()
        response.close()
        return response

class IncludedResponse(object):

    def __init__(self):
        self.headers = None
        self.status = None
        self.output = StringIO()
        self.str = None

    def close(self):
        self.str = self.output.getvalue()
        self.output.close()
        self.output = None

    def write(self):
        assert self.output is not None, "This response has already been closed and no further data can be written."
        self.output.write()

    def __str__(self):
        return self.body

    def body__get(self):
        if self.str is None:
            return self.output.getvalue()
        else:
            return self.str
    body = property(body__get)
