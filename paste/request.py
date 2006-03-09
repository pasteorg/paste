# (c) 2005 Ian Bicking and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""
This module provides helper routines with work directly on a WSGI
environment to solve common requirements.

   * get_cookies(environ)
   * parse_querystring(environ)
   * parse_formvars(environ, all_as_list=False, include_get_vars=True)
   * construct_url(environ, with_query_string=True, with_path_info=True,
                   script_name=None, path_info=None, querystring=None)
   * path_info_split(path_info)
   * path_info_pop(environ)
   * resolve_relative_url(url, environ)

"""
import cgi
import textwrap
from Cookie import SimpleCookie
import urlparse
from util.UserDict24 import UserDict

__all__ = ['get_cookies', 'parse_querystring', 'parse_formvars',
           'construct_url', 'path_info_split', 'path_info_pop',
           'resolve_relative_url']

class environ_getter(object):
    """For delegating an attribute to a key in self.environ."""
    # @@: Also __set__?  Should setting be allowed?
    def __init__(self, key, default=''):
        self.key = key
        self.default = default
    def __get__(self, obj, type=None):
        if type == None:
            return self
        return obj.environ.get(self.key, self.default)

    def __repr__(self):
        return '<Proxy for WSGI environ %r key>' % self.key

class MultiDict(UserDict):
    """Acts as a normal dict, but assumes all values are lists, and
    retrieving an item retrieves the first value in the list. getlist
    retrieves the full list"""
    def __getitem__(self, key):
        return self.data[key][0]

    def getlist(self, key):
        return self.data[key]

    def update(self, dict):
        if isinstance(dct, UserDict):
            self.data.update(dict.data)
        elif isinstance(dict, type(self.data)):
            self.data.update(dict)
        else:
            for k, v in dict.items():
                if self.has_key(k) and isinstance(v, list):
                    self[k].extend(v)
                elif self.has_key(k):
                    self[k].append(v)
                elif not isinstance(v, list):
                    self[k] = [v]
                else:
                    self[k] = v


def get_cookies(environ):
    """
    Gets a cookie object (which is a dictionary-like object) from the
    request environment; caches this value in case get_cookies is
    called again for the same request.

    """
    header = environ.get('HTTP_COOKIE', '')
    if environ.has_key('paste.cookies'):
        cookies, check_header = environ['paste.cookies']
        if check_header == header:
            return cookies
    cookies = SimpleCookie()
    cookies.load(header)
    environ['paste.cookies'] = (cookies, header)
    return cookies

def parse_querystring(environ):
    """
    Parses a query string into a list like ``[(name, value)]``.
    Caches this value in case parse_querystring is called again
    for the same request.

    You can pass the result to ``dict()``, but be aware that keys that
    appear multiple times will be lost (only the last value will be
    preserved).

    """
    source = environ.get('QUERY_STRING', '')
    if not source:
        return []
    if 'paste.parsed_querystring' in environ:
        parsed, check_source = environ['paste.parsed_querystring']
        if check_source == source:
            return parsed
    parsed = cgi.parse_qsl(source, keep_blank_values=True,
                           strict_parsing=False)
    environ['paste.parsed_querystring'] = (parsed, source)
    return parsed

def parse_dict_querystring(environ):
    """Parses a query string like parse_querystring, but returns a multidict

    Caches this value in case parse_dict_querystring is called again
    for the same request.

    Example::

        #environ['QUERY_STRING'] -  day=Monday&user=fred&user=jane
        >>> parsed = parse_dict_querystring(environ)

        >>> parsed['day']
        'Monday'
        >>> parsed['user']
        'fred'
        >>> parsed.getlist['user']
        ['fred', 'jane']

    """
    source = environ.get('QUERY_STRING', '')
    if not source:
        return {}
    if 'paste.parsed_dict_querystring' in environ:
        parsed, check_source = environ['paste.parsed_dict_querystring']
        if check_source == source:
            return parsed
    parsed = cgi.parse_qs(source, keep_blank_values=True,
                           strict_parsing=False)
    multi = MultiDict()
    multi.update(parsed)
    environ['paste.parsed_dict_querystring'] = multi
    return multi

def parse_formvars(environ, all_as_list=False, include_get_vars=True):
    """Parses the request, returning a dictionary of the keys.

    If ``all_as_list`` is true, then all values will be lists.  If
    not, then only values that show up multiple times will be lists.

    If ``include_get_vars`` is true and this was a POST request, then
    GET (query string) variables will also be folded into the
    dictionary.

    All values should be strings, except for file uploads which are
    left as FieldStorage instances.

    """
    source = (environ.get('QUERY_STRING', ''),
              environ['wsgi.input'], environ['REQUEST_METHOD'],
              all_as_list, include_get_vars)
    if 'paste.parsed_formvars' in environ:
        parsed, check_source = environ['paste.parsed_formvars']
        if check_source == source:
            return parsed
    fs = cgi.FieldStorage(fp=environ['wsgi.input'],
                          environ=environ,
                          keep_blank_values=1)
    formvars = {}
    for name in fs.keys():
        values = fs[name]
        if not isinstance(values, list):
            values = [values]
        for value in values:
            if not value.filename:
                value = value.value
            if name in formvars:
                if isinstance(formvars[name], list):
                    formvars[name].append(value)
                else:
                    formvars[name] = [formvars[name], value]
            elif all_as_list:
                formvars[name] = [value]
            else:
                formvars[name] = value
    if environ['REQUEST_METHOD'] == 'POST' and include_get_vars:
        for name, value in parse_querystring(environ):
            if name in formvars:
                if isinstance(formvars[name], list):
                    formvars[name].append(value)
                else:
                    formvars[name] = [formvars[name], value]
            elif all_as_list:
                formvars[name] = [value]
            else:
                formvars[name] = value
    environ['paste.parsed_formvars'] = (formvars, source)
    return formvars

def construct_url(environ, with_query_string=True, with_path_info=True,
                  script_name=None, path_info=None, querystring=None):
    """Reconstructs the URL from the WSGI environment.

    You may override SCRIPT_NAME, PATH_INFO, and QUERYSTRING with
    the keyword arguments.

    """
    url = environ['wsgi.url_scheme']+'://'

    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST'].split(':')[0]
    else:
        url += environ['SERVER_NAME']

    if environ['wsgi.url_scheme'] == 'https':
        if environ['SERVER_PORT'] != '443':
            url += ':' + environ['SERVER_PORT']
    else:
        if environ['SERVER_PORT'] != '80':
            url += ':' + environ['SERVER_PORT']

    if script_name is None:
        url += environ.get('SCRIPT_NAME','')
    else:
        url += script_name
    if with_path_info:
        if path_info is None:
            url += environ.get('PATH_INFO','')
        else:
            url += path_info
    if with_query_string:
        if querystring is None:
            if environ.get('QUERY_STRING'):
                url += '?' + environ['QUERY_STRING']
        elif querystring:
            url += '?' + querystring
    return url

def resolve_relative_url(url, environ):
    """
    Resolve the given relative URL as being relative to the
    location represented by the environment.  This can be used
    for redirecting to a relative path.  Note: if url is already
    absolute, this function will (intentionally) have no effect
    on it.

    """
    cur_url = construct_url(environ, with_query_string=False)
    return urlparse.urljoin(cur_url, url)

def path_info_split(path_info):
    """
    Splits off the first segment of the path.  Returns (first_part,
    rest_of_path).  first_part can be None (if PATH_INFO is empty), ''
    (if PATH_INFO is '/'), or a name without any /'s.  rest_of_path
    can be '' or a string starting with /.

    """
    if not path_info:
        return None, ''
    assert path_info.startswith('/'), (
        "PATH_INFO should start with /: %r" % path_info)
    path_info = path_info.lstrip('/')
    if '/' in path_info:
        first, rest = path_info.split('/', 1)
        return first, '/' + rest
    else:
        return path_info, ''

def path_info_pop(environ):
    """
    'Pops' off the next segment of PATH_INFO, pushing it onto
    SCRIPT_NAME, and returning that segment.

    For instance::

        >>> def call_it(script_name, path_info):
        ...     env = {'SCRIPT_NAME': script_name, 'PATH_INFO': path_info}
        ...     result = path_info_pop(env)
        ...     print 'SCRIPT_NAME=%r; PATH_INFO=%r; returns=%r' % (
        ...         env['SCRIPT_NAME'], env['PATH_INFO'], result)
        >>> call_it('/foo', '/bar')
        SCRIPT_NAME='/foo/bar'; PATH_INFO=''; returns='bar'
        >>> call_it('/foo/bar', '')
        SCRIPT_NAME='/foo/bar'; PATH_INFO=''; returns=None
        >>> call_it('/foo/bar', '/')
        SCRIPT_NAME='/foo/bar/'; PATH_INFO=''; returns=''
        >>> call_it('', '/1/2/3')
        SCRIPT_NAME='/1'; PATH_INFO='/2/3'; returns='1'
        >>> call_it('', '//1/2')
        SCRIPT_NAME='//1'; PATH_INFO='/2'; returns='1'

    """
    path = environ.get('PATH_INFO', '')
    if not path:
        return None
    while path.startswith('/'):
        environ['SCRIPT_NAME'] += '/'
        path = path[1:]
    if '/' not in path:
        environ['SCRIPT_NAME'] += path
        environ['PATH_INFO'] = ''
        return path
    else:
        segment, path = path.split('/', 1)
        environ['PATH_INFO'] = '/' + path
        environ['SCRIPT_NAME'] += segment
        return segment

_parse_headers_special = {
    # This is a Zope convention, but we'll allow it here:
    'HTTP_CGI_AUTHORIZATION': 'Authorization',
    'CONTENT_LENGTH': 'Content-Length',
    'CONTENT_TYPE': 'Content-Type',
    }

def parse_headers(environ):
    """
    Parse the headers in the environment (like ``HTTP_HOST``) and
    yield a sequence of those (header_name, value) tuples.
    """
    # @@: Maybe should parse out comma-separated headers?
    for cgi_var, value in environ.iteritems():
        if cgi_var in _parse_headers_special:
            yield _parse_headers_special[cgi_var], value
        elif cgi_var.startswith('HTTP_'):
            yield cgi_var[5:].title().replace('_', '-'), value

class LazyCache(object):
    """Lazy and Caching Function Executer

    LazyCache takes a function, and will hold onto it to be called at a
    later time. When the function is called, its result will be cached and
    used when called in the future.

    This style is ideal for functions that may require processing that is
    only done in rare cases, but when it is done, caching the results is
    desired.

    """
    def __init__(self, func):
        self.fn = func
        self.result = None

    def __call__(self, *args):
        if not self.result:
            self.result = self.fn(*args)
        return self.result

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
        self.urlvars = urlvars
    
    body = environ_getter('wsgi.input')
    scheme = environ_getter('wsgi.url_scheme') # ?
    method = environ_getter('REQUEST_METHOD')
    # wsgi.config would be better, of course:
    config = environ_getter('paste.config')
    script_name = environ_getter('SCRIPT_NAME')
    path_info = environ_getter('PATH_INFO')
    # Other possible variables:
    # REMOTE_USER, CONTENT_TYPE, CONTENT_LENGTH?  Probably not
    # REMOTE_ADDR, REMOTE_HOST, AUTH_TYPE?  Even less interesting
    # SERVER_PORT?  Maybe
    # SERVER_PROTOCOL, SERVER_SOFTWARE, GATEWAY_INTERFACE?  Definitely not

    def host(self):
        """Host name provided in HTTP_HOST, with fall-back to SERVER_NAME"""
        return self.environ.get('HTTP_HOST', self.environ.get('SERVER_NAME'))
    host = property(host, doc=host.__doc__)

    def get(self):
        """
        Dictionary-like object representing the QUERY_STRING
        parameters. Always present, if possibly empty.

        If the same key is present in the query string multiple
        times, it will be present as a list.
        """
        return parse_dict_querystring(self.environ)
    get = property(get, doc=get.__doc__)

    def post(self):
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
    post = property(LazyCache(post), doc=post.__doc__)

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
        pms.update(self.post)
        pms.update(self.get)
        return pms
    params = property(params, doc=params.__doc__)

    def urlvars(self):
        """
        Return a plain dictionary representing any variables
        captured from the URL parsing (the parsed URL portion is in
        SCRIPT_NAME); frequently {}, but never None
        """
        return self.urlvars
    urlvars = property(urlvars, doc=urlvars.__doc__)

    def cookies(self):
        """Dictionary of cookies keyed by cookie name.

        Just a plain dictionary, may be empty but not None.
        
        """
        fresh_cookies = get_cookies(self.environ)
        cookie_dict = {}
        for k, morsel in fresh_cookies.iteritems():
            cookie_dict[k] = morsel.value
        return cookie_dict
    cookies = property(LazyCache(cookies), doc=cookies.__doc__)

    def headers(self):
        """Access to incoming headers"""
        headertable = {}
        for key in self.environ.keys():
            if key.startswith('HTTP'):
                headertable[key[5:]] = self.environ[key]
        return headertable
    headers = property(LazyCache(headers), doc=headers.__doc__)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
