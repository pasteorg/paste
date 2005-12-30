# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Middleware to make internal requests and forward requests internally.
"""

from cStringIO import StringIO

__all__ = ['RecursiveMiddleware']

class RecursiveMiddleware(object):

    """
    A WSGI middleware that allows for recursive and forwarded calls.
    All these calls go to the same 'application', but presumably that
    application acts differently with different URLs.  The forwarded
    URLs must be relative to this container.

    Interface is entirely through the ``paste.recursive.forward`` and
    ``paste.recursive.include`` environmental keys.
    """

    def __init__(self, application, global_conf=None):
        self.application = application

    def __call__(self, environ, start_response):
        environ['paste.recursive.forward'] = Forwarder(
            self.application, environ, start_response)
        environ['paste.recursive.include'] = Includer(
            self.application, environ, start_response)
        return self.application(environ, start_response)

class Recursive(object):

    def __init__(self, application, environ, start_response):
        self.application = application
        self.original_environ = environ.copy()
        self.previous_environ = environ
        self.start_response = start_response

    def __call__(self, path, new_environ=None):
        """
        `extra_environ` is an optional dictionary that is also added
        to the forwarded request.  E.g., ``{'HTTP_HOST': 'new.host'}``
        could be used to forward to a different virtual host.
        """
        environ = self.original_environ.copy()
        if new_environ:
            environ.update(new_environ)
        environ['paste.recursive.previous_environ'] = self.previous_environ
        base_path = self.original_environ.get('SCRIPT_NAME')
        if path.startswith('/'):
            assert path.startswith(base_path), (
                "You can only forward requests to resources under the "
                "path %r (not %r)" % (base_path, path))
            path = path[len(base_path)+1:]
        assert not path.startswith('/')
        path_info = '/' + path
        environ['PATH_INFO'] = path_info
        return self.activate(environ)

    def __repr__(self):
        return '<%s.%s from %s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.original_environ.get('SCRIPT_NAME') or '/')

class Forwarder(Recursive):

    """
    The forwarder will try to restart the request, except with
    the new `path` (replacing ``PATH_INFO`` in the request).

    It must not be called after and headers have been returned.
    It returns an iterator that must be returned back up the call
    stack, so it must be used like::

        return environ['paste.recursive.forward'](path)

    Meaningful transformations cannot be done, since headers are
    sent directly to the server and cannot be inspected or
    rewritten.
    """

    def activate(self, environ):
        return self.application(environ, self.start_response)
    

class Includer(Recursive):

    """
    Starts another request with the given path and adding or
    overwriting any values in the `extra_environ` dictionary.
    Returns an IncludeResponse object.
    """
    
    def activate(self, environ):
        response = IncludedResponse()
        def start_response(status, headers, exc_info=None):
            if exc_info:
                raise exc_info[0], exc_info[1], exc_info[2]
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

    def write(self, s):
        assert self.output is not None, (
            "This response has already been closed and no further data "
            "can be written.")
        self.output.write(s)

    def __str__(self):
        return self.body

    def body__get(self):
        if self.str is None:
            return self.output.getvalue()
        else:
            return self.str
    body = property(body__get)

