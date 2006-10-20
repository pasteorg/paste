# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""WSGI Wrappers for a Request and Response

The WSGIRequest and WSGIResponse objects are light wrappers to make it easier
to deal with an incoming request and sending a response.
"""
import re
import warnings
from paste.request import EnvironHeaders, parse_formvars, parse_dict_querystring, get_cookie_dict
from paste.util.multidict import MultiDict
from paste.response import HeaderDict
from paste.wsgilib import encode_unicode_app_iter
import paste.registry as registry
from Cookie import SimpleCookie

# settings should be set with the registry to a dict having at least:
#     content_type, charset
# With the optional:
#     encoding_errors (specifies a codec error handler, defaults to 'strict')
settings = registry.StackedObjectProxy(default=dict(content_type='text/html', 
    charset='UTF-8', encoding_errors='strict'))

class environ_getter(object):
    """For delegating an attribute to a key in self.environ."""
    # @@: Also __set__?  Should setting be allowed?
    def __init__(self, key, default='', default_factory=None):
        self.key = key
        self.default = default
        self.default_factory = default_factory
    def __get__(self, obj, type=None):
        if type is None:
            return self
        if self.key not in obj.environ:
            if self.default_factory:
                val = obj.environ[self.key] = self.default_factory()
                return val
            else:
                return self.default
        return obj.environ[self.key]

    def __repr__(self):
        return '<Proxy for WSGI environ %r key>' % self.key

class WSGIRequest(object):
    """WSGI Request API Object

    This object represents a WSGI request with a more friendly interface.
    This does not expose every detail of the WSGI environment, and does not
    in any way express anything beyond what is available in the environment
    dictionary.  *All* state is kept in the environment dictionary; this
    is essential for interoperability.

    You are free to subclass this object.

    """
    def __init__(self, environ):
        self.environ = environ
        # This isn't "state" really, since the object is derivative:
        self.headers = EnvironHeaders(environ)
    
    body = environ_getter('wsgi.input')
    scheme = environ_getter('wsgi.url_scheme')
    method = environ_getter('REQUEST_METHOD')
    script_name = environ_getter('SCRIPT_NAME')
    path_info = environ_getter('PATH_INFO')
    urlvars = environ_getter('paste.urlvars', default_factory=dict)
    
    def is_xhr(self):
        """Returns a boolean if X-Requested-With is present and a XMLHttpRequest"""
        return self.environ.get('HTTP_X_REQUESTED_WITH', '') == 'XMLHttpRequest'
    is_xhr = property(is_xhr, doc=is_xhr.__doc__)
    
    def host(self):
        """Host name provided in HTTP_HOST, with fall-back to SERVER_NAME"""
        return self.environ.get('HTTP_HOST', self.environ.get('SERVER_NAME'))
    host = property(host, doc=host.__doc__)

    def GET(self):
        """
        Dictionary-like object representing the QUERY_STRING
        parameters. Always present, if possibly empty.

        If the same key is present in the query string multiple
        times, it will be present as a list.
        """
        return parse_dict_querystring(self.environ)
    GET = property(GET, doc=GET.__doc__)

    def POST(self):
        """Dictionary-like object representing the POST body.

        Most values are strings, but file uploads can be FieldStorage
        objects. If this is not a POST request, or the body is not
        encoded fields (e.g., an XMLRPC request) then this will be empty.

        This will consume wsgi.input when first accessed if applicable,
        but the output will be put in environ['paste.post_vars']
        
        """
        return parse_formvars(self.environ, include_get_vars=False)
    POST = property(POST, doc=POST.__doc__)

    def params(self):
        """MultiDict of keys from POST, GET, URL dicts

        Return a key value from the parameters, they are checked in the
        following order: POST, GET, URL

        Additional methods supported:

        ``getlist(key)``
            Returns a list of all the values by that key, collected from
            POST, GET, URL dicts
        """
        pms = MultiDict()
        pms.update(self.POST)
        pms.update(self.GET)
        return pms
    params = property(params, doc=params.__doc__)

    def cookies(self):
        """Dictionary of cookies keyed by cookie name.

        Just a plain dictionary, may be empty but not None.
        
        """
        return get_cookie_dict(self.environ)
    cookies = property(cookies, doc=cookies.__doc__)

_CHARSET_RE = re.compile(r'.*;\s*charset=(.*?)(;|$)', re.I)
class WSGIResponse(object):
    """A basic HTTP response with content, headers, and out-bound cookies"""
    def __init__(self, content='', mimetype=None, code=200):
        self._iter = None
        self._is_str_iter = True

        self.content = content
        self.headers = HeaderDict()
        self.cookies = SimpleCookie()
        self.status_code = code
        if not mimetype:
            mimetype = "%s; charset=%s" % (settings['content_type'],
                                           settings['charset'])
        self.headers['Content-Type'] = mimetype

        if 'encoding_errors' in settings:
            self.encoding_errors = settings['encoding_errors']
        else:
            self.encoding_errors = 'strict'

    def __str__(self):
        """Returns a rendition of the full HTTP message, including headers.

        When the content is an iterator, the actual content is replaced with the
        output of str(iterator) (to avoid exhausting the iterator).
        """
        if self._is_str_iter:
            content = ''.join(self.get_content_as_string())
        else:
            content = str(self.content)
        return '\n'.join(['%s: %s' % (key, value)
            for key, value in self.headers.headeritems()]) \
            + '\n\n' + content
    
    def __call__(self, environ, start_response):
        """Conveinence call to return output and set status information
        
        Conforms to the WSGI interface for calling purposes only.
        
        Example usage:
        
        .. code-block:: Python

            def wsgi_app(environ, start_response):
                response = WSGIResponse()
                response.write("Hello world")
                response.headers['Content-Type'] = 'latin1'
                return response(environ, start_response)
        
        """
        status_text = STATUS_CODE_TEXT[self.status_code]
        status = '%s %s' % (self.status_code, status_text)
        response_headers = self.headers.headeritems()
        for c in self.cookies.values():
            response_headers.append(('Set-Cookie', c.output(header='')))
        start_response(status, response_headers)
        is_file = isinstance(self.content, file)
        if 'wsgi.file_wrapper' in environ and is_file:
            return environ['wsgi.file_wrapper'](self.content)
        elif is_file:
            return iter(lambda: self.content.read(), '')
        return self.get_content_as_string()
    
    def determine_encoding(self):
        """
        Determine the encoding as specified by the Content-Type's charset
        parameter, if one is set
        """
        charset_match = _CHARSET_RE.match(self.headers.get('Content-Type', ''))
        if charset_match:
            return charset_match.group(1)
        # No charset specified, default to iso-8859-1 as per RFC2616
        return 'iso-8859-1'
    
    def has_header(self, header):
        """
        Case-insensitive check for a header
        """
        warnings.warn('WSGIResponse.has_header is deprecated, use '
                      'WSGIResponse.headers.has_key instead', DeprecationWarning,
                      2)
        return self.headers.has_key(header)

    def set_cookie(self, key, value='', max_age=None, expires=None, path='/',
                   domain=None, secure=None):
        """
        Define a cookie to be sent via the outgoing HTTP headers
        """
        self.cookies[key] = value
        for var_name, var_value in [
            ('max_age', max_age), ('path', path), ('domain', domain),
            ('secure', secure), ('expires', expires)]:
            if var_value is not None:
                self.cookies[key][var_name.replace('_', '-')] = var_value

    def delete_cookie(self, key, path='/', domain=None):
        """
        Notify the browser the specified cookie has expired and should be
        deleted (via the outgoing HTTP headers)
        """
        self.cookies[key] = ''
        if path is not None:
            self.cookies[key]['path'] = path
        if domain is not None:
            self.cookies[key]['domain'] = path
        self.cookies[key]['expires'] = 0
        self.cookies[key]['max-age'] = 0

    def _set_content(self, content):
        if hasattr(content, '__iter__'):
            self._iter = content
            if isinstance(content, list):
                self._is_str_iter = True
            else:
                self._is_str_iter = False
        else:
            self._iter = [content]
            self._is_str_iter = True
    content = property(lambda self: self._iter, _set_content,
                       doc='Get/set the specified content, where content can '
                       'be: a string, a list of strings, a generator function '
                       'that yields strings, or an iterable object that '
                       'produces strings.')

    def get_content_as_string(self):
        """
        Returns the content as an iterable of strings, encoding each element of
        the iterator from a Unicode object if necessary.
        """
        return encode_unicode_app_iter(self.content, self.determine_encoding(),
                                       self.encoding_errors)
    
    def wsgi_response(self):
        """
        Return this WSGIResponse as a tuple of WSGI formatted data, including:
        (status, headers, iterable)
        """
        status_text = STATUS_CODE_TEXT[self.status_code]
        status = '%s %s' % (self.status_code, status_text)
        response_headers = self.headers.headeritems()
        for c in self.cookies.values():
            response_headers.append(('Set-Cookie', c.output(header='')))
        return status, response_headers, self.get_content_as_string()
    
    # The remaining methods partially implement the file-like object interface.
    # See http://docs.python.org/lib/bltin-file-objects.html
    def write(self, content):
        if not self._is_str_iter:
            raise IOError, "This %s instance's content is not writable: (content " \
                'is an iterator)' % self.__class__.__name__
        self.content.append(content)

    def flush(self):
        pass

    def tell(self):
        if not self._is_str_iter:
            raise IOError, 'This %s instance cannot tell its position: (content ' \
                'is an iterator)' % self.__class__.__name__
        return sum([len(chunk) for chunk in self._iter])

## @@ I'd love to remove this, but paste.httpexceptions.get_exception
##    doesn't seem to work...
# See http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
STATUS_CODE_TEXT = {
    100: 'CONTINUE',
    101: 'SWITCHING PROTOCOLS',
    200: 'OK',
    201: 'CREATED',
    202: 'ACCEPTED',
    203: 'NON-AUTHORITATIVE INFORMATION',
    204: 'NO CONTENT',
    205: 'RESET CONTENT',
    206: 'PARTIAL CONTENT',
    300: 'MULTIPLE CHOICES',
    301: 'MOVED PERMANENTLY',
    302: 'FOUND',
    303: 'SEE OTHER',
    304: 'NOT MODIFIED',
    305: 'USE PROXY',
    306: 'RESERVED',
    307: 'TEMPORARY REDIRECT',
    400: 'BAD REQUEST',
    401: 'UNAUTHORIZED',
    402: 'PAYMENT REQUIRED',
    403: 'FORBIDDEN',
    404: 'NOT FOUND',
    405: 'METHOD NOT ALLOWED',
    406: 'NOT ACCEPTABLE',
    407: 'PROXY AUTHENTICATION REQUIRED',
    408: 'REQUEST TIMEOUT',
    409: 'CONFLICT',
    410: 'GONE',
    411: 'LENGTH REQUIRED',
    412: 'PRECONDITION FAILED',
    413: 'REQUEST ENTITY TOO LARGE',
    414: 'REQUEST-URI TOO LONG',
    415: 'UNSUPPORTED MEDIA TYPE',
    416: 'REQUESTED RANGE NOT SATISFIABLE',
    417: 'EXPECTATION FAILED',
    500: 'INTERNAL SERVER ERROR',
    501: 'NOT IMPLEMENTED',
    502: 'BAD GATEWAY',
    503: 'SERVICE UNAVAILABLE',
    504: 'GATEWAY TIMEOUT',
    505: 'HTTP VERSION NOT SUPPORTED',
}
