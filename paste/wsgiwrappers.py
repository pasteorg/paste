import paste.httpexceptions
from paste.request import EnvironHeaders, parse_formvars, parse_dict_querystring, get_cookie_dict, MultiDict
from paste.response import HeaderDict
import paste.registry as registry
import paste.httpexceptions
from Cookie import SimpleCookie

# This should be set with the registry to a dict having at least:
#     content_type, charset
settings = registry.StackedObjectProxy(default=dict(content_type='text/html', 
    charset='UTF-8'))

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
    def __init__(self, environ, urlvars={}):
        self.environ = environ
        # This isn't "state" really, since the object is derivative:
        self.headers = EnvironHeaders(environ)
    
    body = environ_getter('wsgi.input')
    scheme = environ_getter('wsgi.url_scheme')
    method = environ_getter('REQUEST_METHOD')
    script_name = environ_getter('SCRIPT_NAME')
    path_info = environ_getter('PATH_INFO')
    urlvars = environ_getter('paste.urlvars', default_factory=dict)
    
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
        formvars = MultiDict()
        formvars.update(parse_formvars(self.environ, all_as_list=True, include_get_vars=False))
        return formvars
    POST = property(POST, doc=POST.__doc__)

    def params(self):
        """MultiDict of keys from POST, GET, URL dicts

        Return a key value from the parameters, they are checked in the
        following order:
            POST, GET, URL

        Additional methods supported:

        getlist(key)
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

class WSGIResponse(object):
    "A basic HTTP response, with content and dictionary-accessed headers"
    def __init__(self, content='', mimetype=None, code=200):
        if not mimetype:
            mimetype = "%s; charset=%s" % (settings['content_type'], settings['charset'])
        self.content = [content]
        self.headers = HeaderDict()
        self.headers['Content-Type'] = mimetype
        self.cookies = SimpleCookie()
        self.status_code = code

    def __str__(self):
        "Full HTTP message, including headers"
        return '\n'.join(['%s: %s' % (key, value)
            for key, value in self.headers.items()]) \
            + '\n\n' + ''.join(self.content)
    
    def has_header(self, header):
        "Case-insensitive check for a header"
        header = header.lower()
        for key in self.headers.keys():
            if key.lower() == header:
                return True
        return False

    def set_cookie(self, key, value='', max_age=None, expires=None, path='/', domain=None, secure=None):
        self.cookies[key] = value
        for var in ('max_age', 'path', 'domain', 'secure', 'expires'):
            val = locals()[var]
            if val is not None:
                self.cookies[key][var.replace('_', '-')] = val

    def delete_cookie(self, key):
        try:
            self.cookies[key]['max_age'] = 0
        except KeyError:
            pass

    def get_content_as_string(self, encoding):
        """
        Returns the content as a string, encoding it from a Unicode object if
        necessary.
        """
        if isinstance(self.content, unicode):
            return [''.join(self.content).encode(encoding)]
        return self.content
    
    def wsgi_response(self, encoding=None):
        if not encoding:
            encoding = settings['charset']
        status_text = STATUS_CODE_TEXT[self.status_code]
        status = '%s %s' % (self.status_code, status_text)
        response_headers = self.headers.items()
        for c in self.cookies.values():
            response_headers.append(('Set-Cookie', c.output(header='')))
        output = self.get_content_as_string(encoding)
        return status, response_headers, output
    
    # The remaining methods partially implement the file-like object interface.
    # See http://docs.python.org/lib/bltin-file-objects.html
    def write(self, content):
        self.content.append(content)

    def flush(self):
        pass

    def tell(self):
        return len(self.content)

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