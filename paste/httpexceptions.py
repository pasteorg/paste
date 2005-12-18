# (c) 2005 Ian Bicking, Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# Some of this code was funded by http://prometheusresearch.com
"""
HTTP Exception Middleware

This module processes Python exceptions that relate to HTTP exceptions
by defining a set of exceptions, all subclasses of HTTPException, and a
request handler (`middleware`) that catches these exceptions and turns
them into proper responses.

This module defines exceptions according to RFC 2068 [1]: codes with
100-300 are not really errors; 400's are client errors, and 500's are
server errors.  According to the WSGI specification [2], the application
can call ``start_response`` more then once only under two conditions:
(a) the response has not yet been sent, or (b) if the second and
subsequent invocations of ``start_response`` have a valid ``exc_info``
argument obtained from ``sys.exc_info()``.  The WSGI specification then
requires the server or gateway to handle the case where content has been
sent and then an exception was encountered.  

Exceptions in the 5xx range and those raised after ``start_response``
has been called are treated as serious errors and the ``exc_info`` is
filled-in with information needed for a lower level module to generate a
stack trace and log information.

References:
[1] http://www.python.org/peps/pep-0333.html#error-handling
[2] http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.5

Exception
  HTTPException
    HTTPRedirection
      # 300 Multiple Choices
      301 - HTTPMovedPermanently
      302 - HTTPFound
      303 - HTTPSeeOther
      304 - HTTPNotModified
      305 - HTTPUseProxy
      # 306 Unused
      307 - HTTPTemporaryRedirect
    HTTPError
      HTTPClientError
        400 - HTTPBadRequest
        401 - HTTPUnauthorized
        # 402 Payment Required
        403 - HTTPForbidden
        404 - HTTPNotFound
        405 - HTTPMethodNotAllowed
        406 - HTTPNotAcceptable
        # 407 Proxy Authentication Required
        # 408 Request Timeout
        409 - HTTPConfict
        410 - HTTPGone
        411 - HTTPLengthRequired
        412 - HTTPPreconditionFailed
        413 - HTTPRequestEntityTooLarge
        414 - HTTPRequestURITooLong
        415 - HTTPUnsupportedMediaType
        416 - HTTPRequestRangeNotSatisfiable
        417 - HTTPExpectationFailed
      HTTPServerError
        500 - HTTPInternalServerError
        501 - HTTPNotImplemented
        502 - HTTPBadGateway
        503 - HTTPServiceUnavailable
        504 - HTTPGatewayTimeout
        505 - HTTPVersionNotSupported
"""

import types
from wsgilib import catch_errors_app
from response import has_header, header_value
from util.quoting import strip_html, html_quote

class HTTPException(Exception):
    """ 
    Base class for all HTTP exceptions

    This encapsulates an HTTP response that interrupts normal application 
    flow; but one which is not necessarly an error condition. For
    example, codes in the 300's are exceptions in that they interrupt
    normal processing; however, they are not considered errors. 
    
    This class is complicated by 4 factors:

      1. The content given to the exception may either be plain-text or
         as html-text. 
   
      2. The template may want to have string-substitutions taken from
         the current ``environ`` or values from incoming headers. This
         is especially troublesome due to case sensitivity.
  
      3. The final output may either be text/plain or text/html 
         mime-type as requested by the client application.

      4. Each exception has a default explanation, but those who
         raise exceptions may want to provide additional detail.

    Attributes:

       ``code``       
           the HTTP status code for the exception

       ``title``      
           remainder of the status line (stuff after the code)

       ``explanation``   
           a plain-text explanation of the error message that is
           not subject to environment or header substitutions; 
           it is accessable in the template via %(explanation)s
       
       ``detail``    
           a plain-text message customization that is not subject 
           to environment or header substutions; accessable in 
           the template via %(detail)s

       ``template``   
           a content fragment (in HTML) used for environment and 
           header substution; the default template includes both
           the explanation and further detail provided in the 
           message

       ``required_headers``  
           a sequence of headers which are required for proper
           construction of the exception

    Parameters:

       ``detail``     a plain-text override of the default ``detail``
       ``headers``    a list of (k,v) header pairs  
       ``comment``    a plain-text additional information which is
                      usually stripped/hidden for end-users

    To override the template (which is HTML content) or the plain-text
    explanation, one must subclass the given exception; or customize it
    after it has been created.  This particular breakdown of a message
    into explanation, detail and template allows both the creation of
    plain-text and html messages for various clients as well as
    error-free substution of environment variables and headers.
    """

    code = None
    title = None
    explanation = ''
    detail = ''
    comment = ''
    template = "%(explanation)s\n<br/>%(detail)s\n<!-- %(comment)s -->"
    required_headers = ()
    server_name = 'WSGI server'

    def __init__(self, detail=None, headers=None, comment=None):
        assert self.code, "Do not directly instantiate abstract exceptions."
        assert isinstance(headers, (type(None), list))
        assert isinstance(detail, (type(None), basestring))
        assert isinstance(comment, (type(None), basestring))
        self.headers = headers or tuple()
        for req in self.required_headers:
            assert has_header(headers, req)
        if detail is not None:
            self.detail = detail
        if comment is not None:
            self.comment = comment
        Exception.__init__(self,"%s %s\n%s\n%s\n" % (
            self.code, self.title, self.explanation, self.detail))

    def make_body(self, environ, template, escfunc):
        args = {'explanation': escfunc(self.explanation),
                'detail': escfunc(self.detail),
                'comment': escfunc(self.comment)}
        if HTTPException.template == self.template:
            return template % args
        for (k, v) in environ.items():
            args[k] = escfunc(v)
        if self.headers:
            for (k, v) in self.headers:
                args[k.lower()] = escfunc(v)
        return template % args

    def plain(self, environ):
        """ text/plain representation of the exception """
        noop = lambda _: _
        body = self.make_body(environ, strip_html(self.template), noop)
        return ('%s %s\n%s\n' % (self.code, self.title, body))

    def html(self, environ):
        """ text/html representation of the exception """
        body = self.make_body(environ, self.template, html_quote)
        return ('<html><head><title>%(title)s</title></head>\n'
                '<body>\n'
                '<h1>%(title)s</h1>\n'
                '<p>%(body)s</p>\n'
                '<hr noshade>\n'
                '<div align="right">%(server)s</div>\n'
                '</body></html>\n'
                % {'title': self.title,
                   'code': self.code,
                   'server': self.server_name,
                   'body': body})

    def wsgi_application(self, environ, start_response, exc_info=None):
        """
        This exception as a WSGI application
        """
        if 'html' in environ.get('HTTP_ACCEPT',''):
            headers = {'content-type': 'text/html'}
            content = self.html(environ)
        else:
            headers = {'content-type': 'text/plain'}
            content = self.plain(environ)
        if self.headers:
            headers.update(self.headers)
        if isinstance(content, unicode):
            content = content.encode('utf8')
            headers['content_type'] += '; charset=utf8'
        start_response('%s %s' % (self.code, self.title),
                       headers.items(),
                       exc_info)
        return [content]


    def __repr__(self):
        return '<%s %s; code=%s>' % (self.__class__.__name__,
                                     self.title, self.code)

class HTTPError(HTTPException):
    """ 
    This is an exception which indicates that an error has occured, 
    and that any work in progress should not be committed.  These are
    typically results in the 400's and 500's.
    """

#
# 3xx Redirection
#
#  This class of status code indicates that further action needs to be
#  taken by the user agent in order to fulfill the request. The action
#  required MAY be carried out by the user agent without interaction with
#  the user if and only if the method used in the second request is GET or
#  HEAD. A client SHOULD detect infinite redirection loops, since such
#  loops generate network traffic for each redirection. 
#

class HTTPRedirection(HTTPException):
    """ 
    This is an abstract base class for 3xx redirection.  It indicates
    that further action needs to be taken by the user agent in order
    to fulfill the request.  It does not necessarly signal an error
    condition.
    """
    
class _HTTPMove(HTTPRedirection):
    """ 
    Base class for redirections which require a Location field.

    Since a 'Location' header is a required attribute of 301, 302, 303,
    305 and 307 (but not 304), this base class provides the mechanics to
    make this easy.  While this has the same parameters as HTTPException, 
    if a location is not provided in the headers; it is assumed that the
    detail _is_ the location (this for backward compatibility, otherwise
    we'd add a new attribute).
    """
    required_headers = ('location',)
    explanation = 'The resource has been moved to'
    template = (
        '%(explanation)s <a href="%(location)s">%(location)s</a>;\n'
        'you should be redirected automatically.\n'
        '%(detail)s\n<!-- %(comment)s -->')

    def __init__(self, detail=None, headers=None, comment=None):
        assert isinstance(headers, (type(None), list))
        headers = headers or []
        location = header_value(headers,'location')
        if not location:
            location = detail
            detail = ''
            headers.append(('location', location))
        assert location, ("HTTPRedirection specified neither a "
                          "location in the headers nor did it "
                          "provide a detail argument.")
        HTTPRedirection.__init__(self, location, headers, comment)
        if detail is not None:
            self.detail = detail

class HTTPMovedPermanently(_HTTPMove):
    code = 301
    title = 'Moved Permanently'

class HTTPFound(_HTTPMove):
    code = 302
    title = 'Found'
    explanation = 'The resource was found at'

# This one is safe after a POST (the redirected location will be
# retrieved with GET):
class HTTPSeeOther(_HTTPMove):
    code = 303
    title = 'See Other'

class HTTPNotModified(HTTPRedirection):
    # @@: but not always (HTTP section 14.18.1)...?
    required_headers = ('date',)
    code = 304
    title = 'Not Modified'
    message = ''
    # @@: should include date header, optionally other headers
    # @@: should not return a content body
    def plain(self, environ):
        return ''
    def html(self, environ):
        """ text/html representation of the exception """
        return ''

class HTTPUseProxy(_HTTPMove):
    # @@: OK, not a move, but looks a little like one
    code = 305
    title = 'Use Proxy'
    explanation = (
        'The resource must be accessed through a proxy '
        'located at')

class HTTPTemporaryRedirect(_HTTPMove):
    code = 307
    title = 'Temporary Redirect'

#
# 4xx Client Error
#
#  The 4xx class of status code is intended for cases in which the client
#  seems to have erred. Except when responding to a HEAD request, the
#  server SHOULD include an entity containing an explanation of the error
#  situation, and whether it is a temporary or permanent condition. These
#  status codes are applicable to any request method. User agents SHOULD
#  display any included entity to the user. 
# 

class HTTPClientError(HTTPError):
    """ 
    This is an error condition in which the client is presumed to be
    in-error.  This is an expected problem, and thus is not considered
    a bug.  A server-side traceback is not warranted.  Unless specialized,
    this is a '400 Bad Request'
    """
    code = 400
    title = 'Bad Request'
    explanation = 'The server could not understand your request.'

HTTPBadRequest = HTTPClientError

class HTTPUnauthorized(HTTPClientError):
    required_headers = ('WWW-Authenticate',)
    code = 401
    title = 'Unauthorized'
    explanation = (
        'This server could not verify that you are authorized to\n'
        'access the document you requested.  Either you supplied the\n'
        'wrong credentials (e.g., bad password), or your browser\n'
        'does not understand how to supply the credentials required.\n')

class HTTPForbidden(HTTPClientError):
    code = 403
    title = 'Forbidden'
    explanation = ('Access was denied to this resource.')

class HTTPNotFound(HTTPClientError):
    code = 404
    title = 'Not Found'
    explanation = ('The resource could not be found.')

class HTTPMethodNotAllowed(HTTPClientError):
    required_headers = ('allowed',)
    code = 405
    title = 'Method Not Allowed'
    # override template since we need an environment variable
    template = ('The method %(REQUEST_METHOD)s is not allowed for '
                'this resource.\n%(detail)s')

class HTTPNotAcceptable(HTTPClientError):
    code = 406
    title = 'Not Acceptable'
    # override template since we need an environment variable
    template = ('The resource could not be generated that was '
                'acceptable to your browser (content\nof type '
                '%(HTTP_ACCEPT)s).\n%(detail)s')

class HTTPConflict(HTTPClientError):
    code = 409
    title = 'Conflict'
    explanation = ('There was a conflict when trying to complete '
                   'your request.')

class HTTPGone(HTTPClientError):
    code = 410
    title = 'Gone'
    explanation = ('This resource is no longer available.  No forwarding '
                   'address is given.')

class HTTPLengthRequired(HTTPClientError):
    code = 411
    title = 'Length Required'
    explanation = ('Content-Length header required.')

class HTTPPreconditionFailed(HTTPClientError):
    code = 412
    title = 'Precondition Failed'
    explanation = ('Request precondition failed.')

class HTTPRequestEntityTooLarge(HTTPClientError):
    code = 413
    title = 'Request Entity Too Large'
    explanation = ('The body of your request was too large for this server.')

class HTTPRequestURITooLong(HTTPClientError):
    code = 414
    title = 'Request-URI Too Long'
    explanation = ('The request URI was too long for this server.')

class HTTPUnsupportedMediaType(HTTPClientError):
    code = 415
    title = 'Unsupported Media Type'
    # override template since we need an environment variable
    template = ('The request media type %(CONTENT_TYPE)s is not '
                'supported by this server.\n%(detail)s')

class HTTPRequestRangeNotSatisfiable(HTTPClientError):
    code = 416
    title = 'Request Range Not Satisfiable'
    explanation = ('The Range requested is not available.')

class HTTPExpectationFailed(HTTPClientError):
    code = 417
    title = 'Expectation Failed'
    explanation = ('Expectation failed.')

#
# 5xx Server Error
# 
#  Response status codes beginning with the digit "5" indicate cases in
#  which the server is aware that it has erred or is incapable of
#  performing the request. Except when responding to a HEAD request, the
#  server SHOULD include an entity containing an explanation of the error
#  situation, and whether it is a temporary or permanent condition. User
#  agents SHOULD display any included entity to the user. These response
#  codes are applicable to any request method.
#

class HTTPServerError(HTTPError):
    """ 
    This is an error condition in which the server is presumed to be
    in-error.  This is usually unexpected, and thus requires a traceback;
    ideally, opening a support ticket for the customer. Unless specialized,
    this is a '500 Internal Server Error'
    """
    code = 500
    title = 'Internal Server Error'
    explanation = ('An internal server error occurred.')

HTTPInternalServerError = HTTPServerError
       
class HTTPNotImplemented(HTTPServerError):
    code = 501
    title = 'Not Implemented'
    # override template since we need an environment variable
    template = ('The request method %(REQUEST_METHOD)s is not implemented '
                'for this server.\n%(detail)s')

class HTTPBadGateway(HTTPServerError):
    code = 502
    title = 'Bad Gateway'
    explanation = ('Bad gateway.')

class HTTPServiceUnavailable(HTTPServerError):
    code = 503
    title = 'Service Unavailable'
    explanation = ('The server is currently unavailable. '
                   'Please try again at a later time.')

class HTTPGatewayTimeout(HTTPServerError):
    code = 504
    title = 'Gateway Timeout'
    explanation = ('The gateway has timed out.')

class HTTPVersionNotSupported(HTTPServerError):
    code = 505
    title = 'HTTP Version Not Supported'
    explanation = ('The HTTP version is not supported.')

# abstract HTTP related exceptions
__all__ = ['HTTPException', 'HTTPRedirection', 'HTTPError' ]

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

class HTTPExceptionHandler:
    """
    This middleware catches any exceptions (which are subclasses of
    ``HTTPException``) and turns them into proper HTTP responses. 
    
    Attributes:

       ``warning_level``  
           This attribute determines for what exceptions a stack 
           trace is kept for lower level reporting; by default, it
           only keeps stack trace for 5xx, HTTPServerError exceptions.
           To keep a stack trace for 4xx, HTTPClientError exceptions,
           set this to 400.



    Note if the headers have already been sent, the stack trace is
    always maintained as this indicates a programming error.

    """

    def __init__(self, application, warning_level=None):
        assert not warning_level or ( warning_level > 99 and
                                      warning_level < 600)
        self.warning_level = warning_level or 500
        self.application = application

    def __call__(self, environ, start_response):
        environ['paste.httpexceptions'] = self
        environ.setdefault('paste.expected_exceptions', 
                           []).append(HTTPException)
        return catch_errors_app(
            self.application, environ, start_response,
            self.send_http_response, catch=HTTPException)

    def send_http_response(self, environ, start_response, exc_info):
        try:
            exc = exc_info[1]
            return exc.wsgi_application(environ, start_response, exc_info)
        finally:
            exc_info = None

def middleware(*args, **kw):
    import warnings
    # deprecated 13 dec 2005
    warnings.warn('httpexceptions.middleware is deprecated; use '
                  'make_middleware or HTTPExceptionHandler instead',
                  DeprecationWarning, 2)
    return make_middleware(*args, **kw)

def make_middleware(app, global_conf=None, warning_level=None):
    """
    ``httpexceptions`` middleware; this catches any
    ``paste.httpexceptions.HTTPException`` exceptions (exceptions like
    ``HTTPNotFound``, ``HTTPMovedPermanently``, etc) and turns them
    into proper HTTP responses.

    ``warning_level`` can be an integer corresponding to an HTTP code.
    Any code over that value will be passed 'up' the chain, potentially
    reported on by another piece of middleware.
    """
    if warning_level:
        warning_level = int(warning_level)
    return HTTPExceptionHandler(app, warning_level=warning_level)

__all__.extend(['HTTPExceptionHandler', 'get_exception'])

