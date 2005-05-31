import cgi
import urllib
import warnings
import inspect
import Cookie as CookieEngine

__all__ = ['NoDefault', 'htmlEncode', 'htmlDecode',
           'urlEncode', 'urlDecode',
           ]

try:
    from MiscUtils import NoDefault
except ImportError:
    class NoDefault:
        pass

def htmlEncode(s):
    return cgi.escape(s, 1)

def htmlDecode(s):
    for char, code in [('&', '&amp;'),
                       ('<', '&lt;'),
                       ('>', '&gt;'),
                       ('"', '&quot;')]:
        s = s.replace(code, char)
    return s

urlDecode = urllib.unquote
urlEncode = urllib.quote

def requestURI(dict):
    """
    Returns the request URI for a given CGI-style dictionary. Uses
    REQUEST_URI if available, otherwise constructs and returns it from
    SCRIPT_NAME, PATH_INFO and QUERY_STRING.
    """
    uri = dict.get('REQUEST_URI', None)
    if uri is None:
        uri = dict.get('SCRIPT_NAME', '') + dict.get('PATH_INFO', '')
        query = dict.get('QUERY_STRING', '')
        if query:
            uri = uri + '?' + query
    return uri

def deprecated(msg=None):
    # @@: Right now this takes up a surprising amount of CPU time
    # (blech!  inspect is slow)
    return
    if not msg:
        frame = inspect.stack()[1]
        methodName = frame[3]
        msg = 'The use of %s is deprecated' % methodName
    warnings.warn(msg, DeprecationWarning, stacklevel=3)



class Cookie:
    """
    Cookie is used to create cookies that have additional
    attributes beyond their value.

    Note that web browsers don't typically send any information
    with the cookie other than it's value. Therefore
    `HTTPRequest.cookie` simply returns a value such as an
    integer or a string.

    When the server sends cookies back to the browser, it can send
    a cookie that simply has a value, or the cookie can be
    accompanied by various attributes (domain, path, max-age, ...)
    as described in `RFC 2109`_. Therefore, in HTTPResponse,
    `setCookie` can take either an instance of the Cookie class,
    as defined in this module, or a value.

    Note that Cookies values get pickled (see the `pickle` module),
    so you can set and get cookies that are integers, lists,
    dictionaries, etc.

    .. _`RFC 2109`: ftp://ftp.isi.edu/in-notes/rfc2109.txt
    """

    ## Future
    ##
    ##    * This class should provide error checking in the setFoo()
    ##      methods. Or maybe our internal Cookie implementation
    ##      already does that?
    ##    * This implementation is probably not as efficient as it
    ##      should be, [a] it works and [b] the interface is stable.
    ##      We can optimize later.

    def __init__(self, name, value):
        """
        Create a cookie -- properties other than `name` and
        `value` are set with methods.
        """
        
        self._cookies = CookieEngine.SimpleCookie()
        self._name = name
        self._value = value
        self._cookies[name] = value
        self._cookie = self._cookies[name]

    """
    **Accessors**
    """

    def comment(self):
        return self._cookie['comment']

    def domain(self):
        return self._cookie['domain']

    def maxAge(self):
        return self._cookie['max-age']

    def expires(self):
        return self._cookie['expires']

    def name(self):
        return self._name

    def path(self):
        return self._cookie['path']

    def isSecure(self):
        return self._cookie['secure']

    def value(self):
        return self._value

    def version(self):
        return self._cookie['version']


    """
    **Setters**
    """

    def setComment(self, comment):
        self._cookie['comment'] = comment

    def setDomain(self, domain):
        self._cookie['domain'] = domain

    def setExpires(self, expires):
        self._cookie['expires'] = expires

    def setMaxAge(self, maxAge):
        self._cookie['max-age'] = maxAge

    def setPath(self, path):
        self._cookie['path'] = path

    def setSecure(self, bool):
        self._cookie['secure'] = bool

    def setValue(self, value):
        self._value = value
        self._cookies[self._name] = value

    def setVersion(self, version):
        self._cookie['version'] = version


    """
    **Misc**
    """

    def delete(self):
        """
        When sent, this should delete the cookie from the user's
        browser, by making it empty, expiring it in the past,
        and setting its max-age to 0.  One of these will delete
        the cookie for any browser (which one actually works
        depends on the browser).
        """
        
        self._value = ''
        self._cookie['expires'] = "Mon, 01-Jan-1900 00:00:00 GMT"
        self._cookie['max-age'] = 0
        self._cookie['path'] = '/'


    def headerValue(self):
        """
        Returns a string with the value that should be
        used in the HTTP headers. """
        
        items = self._cookies.items()
        assert(len(items)==1)
        return items[0][1].OutputString()
