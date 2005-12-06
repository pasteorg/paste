# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

"""
WSGI middleware

Processes Python exceptions that relate to HTTP exceptions.  This
defines a set of extensions, all subclasses of HTTPException, and a
middleware (`middleware`) that catches these exceptions and turns them
into proper responses.

Note: if ``'paste.debug_suppress_httpexceptions'`` is in the request
and is true, then this middleware will be skipped.
"""

import types

class HTTPException(Exception):
    code = None
    title = None
    message = None
    # @@: not currently used:
    required_headers = ()
    def __init__(self, message=None, headers=None):
        self.headers = headers
        if message is not None:
            self.message = message
        Exception.__init__(self, self.message)

    def html(self, environ):
        message = self.message
        args = environ.copy()
        if self.headers:
            args.update(self.headers)
        message = message % args
        return ('<html><head><title>%(title)s</title></head>\n'
                '<body>\n'
                '<h1>%(title)s</h1>\n'
                '<p>%(message)s</p>\n'
                '<hr noshade>\n'
                '<div align="right">WSGI server</div>\n'
                '</body></html>\n'
                % {'title': self.title,
                   'code': self.code,
                   'message': message})

    def __repr__(self):
        return '<%s %s; code=%s>' % (self.__class__.__name__,
                                     self.title, self.code)

class _HTTPMove(HTTPException):
    required_headers = ('location',)
    message = ('The resource has been moved to <a href="%(location)s">'
               '%(location)s</a>; you should be redirected automatically.')

class HTTPMovedPermanently(_HTTPMove):
    code = 301
    title = 'Moved Permanently'

class HTTPFound(_HTTPMove):
    code = 302
    title = 'Found'

# This one is safe after a POST (the redirected location will be
# retrieved with GET):
class HTTPSeeOther(_HTTPMove):
    code = 303
    title = 'See Other'

class HTTPNotModified(HTTPException):
    # @@: but not always (HTTP section 14.18.1)...?
    required_headers = ('date',)
    code = 304
    title = 'Not Modified'
    message = ''
    # @@: should include date header, optionally other headers

class HTTPUseProxy(_HTTPMove):
    # @@: OK, not a move, but looks a little like one
    code = 305
    title = 'Use Proxy'
    message = ('This resource must be accessed through the proxy located '
               'at <a href="%(location)s">%(location)s</a>')

class HTTPTemporaryRedirect(_HTTPMove):
    code = 307
    title = 'Temporary Redirect'

class HTTPBadRequest(HTTPException):
    code = 400
    title = 'Bad Request'
    message = ('The server could not understand your request')

class HTTPUnauthorized(HTTPException):
    required_headers = ('WWW-Authenticate',)
    code = 401
    title = 'Unauthorized'
    # @@: should require WWW-Authenticate header
    message = ('Authorization is required to access this resource; '
               'you must login.')

class HTTPForbidden(HTTPException):
    code = 403
    title = 'Forbidden'
    message = ('Access was denied to this resource.')

class HTTPNotFound(HTTPException):
    code = 404
    title = 'Not Found'
    message = ('The resource could not be found.')

class HTTPMethodNotAllowed(HTTPException):
    required_headers = ('allowed',)
    code = 405
    title = 'Method Not Allowed'
    message = ('The method %(REQUEST_METHOD)s is not allowed for this '
               'resource.')

class HTTPNotAcceptable(HTTPException):
    code = 406
    title = 'Not Acceptable'
    message = ('The resource could not be generated that was acceptable '
               'to your browser (content of type %(HTTP_ACCEPT)s).')

class HTTPConfict(HTTPException):
    code = 409
    title = 'Conflict'
    message = ('There was a conflict when trying to complete your '
               'request.')

class HTTPGone(HTTPException):
    code = 410
    title = 'Gone'
    message = ('This resource is no longer available.  No forwarding '
               'address is aavailable.')

class HTTPLengthRequired(HTTPException):
    code = 411
    title = 'Length Required'
    message = ('Content-Length header required.')

class HTTPPreconditionFailed(HTTPException):
    code = 412
    title = 'Precondition Failed'
    message = ('Request precondition failed.')

class HTTPRequestEntityTooLarge(HTTPException):
    code = 413
    title = 'Request Entity Too Large'
    message = ('The body of your request was too large for this server.')

class HTTPRequestURITooLong(HTTPException):
    code = 414
    title = 'Request-URI Too Long'
    message = ('The request URI was too long for this server.')

class HTTPUnsupportedMediaType(HTTPException):
    code = 415
    title = 'Unsupported Media Type'
    message = ('The request media type %(CONTENT_TYPE)s is not '
               'supported by this server.')

class HTTPRequestRangeNotSatisfiable(HTTPException):
    code = 416
    title = 'Request Range Not Satisfiable'
    message = ('The Range requested is not available.')

class HTTPExpectationFailed(HTTPException):
    code = 417
    title = 'Expectation Failed'
    message = ('Expectation failed.')

class HTTPServerError(HTTPException):
    code = 500
    title = 'Internal Server Error'
    message = ('An internal server error occurred.')

class HTTPNotImplemented(HTTPException):
    code = 501
    title = 'Not Implemented'
    message = ('The request method %(REQUEST_METHOD)s is not implemented '
               'for this server.')

class HTTPBadGateway(HTTPException):
    code = 502
    title = 'Bad Gateway'
    message = ('Bad gateway.')

class HTTPServiceUnavailable(HTTPException):
    code = 503
    title = 'Service Unavailable'
    message = ('The server is currently unavailable.  Please try again '
               'at a later time.')

class HTTPGatewayTimeout(HTTPException):
    code = 504
    title = 'Gateway Timeout'
    message = ('The gateway has timed out.')

class HTTPHttpVersionNotSupported(HTTPException):
    code = 505
    title = 'HTTP Version Not Supported'
    message = ('The HTTP version is not supported.')

__all__ = []
_exceptions = {}
for name, value in globals().items():
    if (isinstance(value, (type, types.ClassType)) and
        issubclass(value, HTTPException) and
        value.code):
        _exceptions[value.code] = value
        __all__.append(name)
def get_exception(code):
    return _exceptions[code]

############################################################
## Middleware implementation:
############################################################

def middleware(application, global_conf=None):

    """
    This middleware catches any exceptions (which are subclasses of
    `HTTPException`) and turns them into proper HTTP responses.
    """

    def start_application(environ, start_response):
        environ.setdefault('paste.expected_exceptions', []).append(
            HTTPException)
        app_started = []
        def checked_start_response(status, headers, exc_info=None):
            app_started.append(None)
            return start_response(status, headers, exc_info)
        
        try:
            v = application(environ, checked_start_response)
            environ['paste.expected_exceptions'].remove(HTTPException)
            return v
        except HTTPException, e:
            if environ.get('paste.debug_suppress_httpexceptions'):
                raise
            if app_started:
                # They've already started the response, so we can't
                # do the right thing anymore.
                raise
            headers = {'content-type': 'text/html'}
            if e.headers:
                headers.update(e.headers)
            start_response('%s %s' % (e.code, e.title),
                           headers.items())
            return [e.html(environ)]
        
    return start_application

__all__.extend(['middleware', 'get_exception'])

