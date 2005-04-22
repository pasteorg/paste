"""
A Webware HTTPRequest object, implemented based on the WSGI request
environment dictionary.
"""

import time
import traceback
import cgi
from wkcommon import NoDefault, requestURI, deprecated
from Cookie import SimpleCookie as Cookie

class HTTPRequest(object):

    def __init__(self, transaction, environ):
        self._environ = environ
        self._transaction = transaction
        if environ.has_key('webkit.time'):
            self._time = environ['webkit.time']
        else:
            self._time = time.time()
        self._input = environ['wsgi.input']
        self._setupPath()
        self._setupFields()
        self._setupCookies()
        self._pathInfo = None
        self._serverRootPath = ""
        # @@: I'm leaving out automatic path sessions
        self._sessionExpired = False

    def _setupPath(self):
        self._environ['PATH_INFO'] = self._environ.get('PATH_INFO', '')
        if not self._environ.has_key('REQUEST_URI'):
            self._environ['REQUEST_URI'] = requestURI(self._environ)
        # @@: Not necessarily true for WSGI:
        self._adapterName = self._environ.get('SCRIPT_NAME')

    def _setupFields(self):
        self._fieldStorage = cgi.FieldStorage(
            self._input,
            environ=self._environ,
            keep_blank_values=True,
            strict_parsing=False)
        try:
            keys = self._fieldStorage.keys()
        except TypeError:
            # Maybe an XML-RPC request
            keys = []
        dict = {}
        for key in keys:
            value = self._fieldStorage[key]
            if not isinstance(value, list):
                if not value.filename:
                    # Turn the MiniFieldStorage into a string:
                    value = value.value
            else:
                value = [v.value for v in value]
            dict[key] = value
        if self._environ['REQUEST_METHOD'].upper() == 'POST':
            # Then we must also parse GET variables
            self._getFields = cgi.parse_qs(
                self._environ.get('QUERY_STRING', ''),
                keep_blank_values=True,
                strict_parsing=False)
            for name, value in self._getFields.items():
                if not dict.has_key(name):
                    if isinstance(value, list) and len(value) == 1:
                        # parse_qs always returns a list of lists,
                        # while FieldStorage only uses lists for
                        # keys that actually repeat; this fixes that.
                        value = value[0]
                    dict[name] = value
        self._fields = dict

    def _setupCookies(self):
        cookies = Cookie()
        if self._environ.has_key('HTTP_COOKIE'):
            try:
                cookies.load(self._environ['HTTP_COOKIE'])
            except:
                traceback.print_exc(file=self._environ['wsgi.errors'])
        dict = {}
        for key in cookies.keys():
            dict[key] = cookies[key].value
        self._cookies = dict

    def protocol(self):
        return 'HTTP/1.0'

    def time(self):
        return self._time

    def timeStamp(self):
        return time.asctime(time.localtime(self.time()))

    ## Transactions ##

    def transaction(self):
        return self._transaction

    def setTransaction(self, trans):
        self._transaction = trans

    ## Values ##

    def value(self, name, default=NoDefault):
        if self._fields.has_key(name):
            return self._fields[name]
        else:
            return self.cookie(name, default)

    def hasValue(self, name):
        return self._fields.has_key(name) or self._cookies.has_key(name)

    def extraURLPath(self):
        return self._environ.get('PATH_INFO', '')

    ## Fields ##


    def fieldStorage(self):
        return self._fieldStorage

    def field(self, name, default=NoDefault):
        if default is NoDefault:
            return self._fields[name]
        else:
            return self._fields.get(name, default)

    def hasField(self, name):
        return self._fields.has_key(name)

    def fields(self):
        return self._fields

    def setField(self, name, value):
        self._fields[name] = value

    def delField(self, name):
        del self._fields[name]

    ## Cookies ##

    def cookie(self, name, default=NoDefault):
        """ Returns the value of the specified cookie. """
        if default is NoDefault:
            return self._cookies[name]
        else:
            return self._cookies.get(name, default)

    def hasCookie(self, name):
        return self._cookies.has_key(name)

    def cookies(self):
        """
        Returns a dictionary-style object of all Cookie objects the
        client sent with this request."""
        return self._cookies

    ## Variables passed by server ##
    def serverDictionary(self):
        """
        Returns a dictionary with the data the web server gave us,
        like HTTP_HOST or HTTP_USER_AGENT.  """
        return self._environ

    ## Sessions ##

    def session(self):
        """ Returns the session associated with this request, either
        as specified by sessionId() or newly created. This is a
        convenience for transaction.session() """
        return self._transaction.session()

    def isSessionExpired(self):
        """ Returns bool: whether or not this request originally
        contained an expired session ID.  Only works if the
        Application.config setting "IgnoreInvalidSession" is set to 1;
        otherwise you get a canned error page on an invalid session,
        so your servlet never gets processed.  """
        return self._sessionExpired
    
    def setSessionExpired(self, sessionExpired):
        self._sessionExpired = sessionExpired

    ## Authentication ##

    def remoteUser(self):
        """ Always returns None since authentication is not yet
        supported. Take from CGI variable REMOTE_USER. """
        # @@ 2000-03-26 ce: maybe belongs in section below. clean up docs
        return self._environ['REMOTE_USER']

    ## Remote info ##

    def remoteAddress(self):
        """ Returns a string containing the Internet Protocol (IP)
        address of the client that sent the request. """
        return self._environ['REMOTE_ADDR']

    def remoteName(self):
        """ Returns the fully qualified name of the client that sent
        the request, or the IP address of the client if the name
        cannot be determined. """
        env = self._environ
        return env.get('REMOTE_NAME', env['REMOTE_ADDR'])

    ## Path ##

    def urlPath(self):
        raise NotImplementedError

    def originalURLPath(self):
        environ = self._environ.get('recursive.previous_environ', self._environ)
        url = environ.get("SCRIPT_NAME", '') + environ.get('PATH_INFO', '')
        #self._environ['wsgi.errors'].write('Original URL: %r (from %r)\n' % (url, environ))
        return url
        
    def urlPathDir(self):
        raise NotImplementedError

    def getstate(self):
        raise NotImplementedError
        
    def setURLPath(self, path):
        raise NotImplementedError

    def serverSidePath(self, path=None):
        raise NotImplementedError

    def serverSideContextPath(self, path=None):
        base = self._environ['wsgikit.config']['webkit_dir']
        if path:
            return os.path.join(base, path)
        else:
            return base

    def contextName(self):
        return ''

    def servletURI(self):
        """This is the URI of the servlet, without any query strings or extra path info"""
        # @@: should be implemented
        raise NotImplementedError

    def uriWebKitRoot(self):
        raise NotImplementedError

    def fsPath(self):
        raise NotImplementedError

    def serverURL(self):
        raise NotImplementedError

    def serverURLDir(self):
        raise NotImplementedError

    def siteRoot(self):
        raise NotImplementedError
        
    def siteRootFromCurrentServlet(self):
        raise NotImplementedError
        
    def servletPathFromSiteRoot(self):
        raise NotImplementedError

    ## Special ##

    def adapterName(self):
        """
        Returns the name of the adapter as it appears in the URL.
        Example: '/WebKit.cgi'
        This is useful in special cases when you are constructing URLs. See Testing/Main.py for an example use.
        """
        deprecated()
        return '/'.join(self._environ['SCRIPT_NAME'].split('/')[:-1])

    def rawRequest(self):
        raise NotImplementedError

    def environ(self):
        return self._environ

    def rawInput(self, rewind=0):
        """
        This gives you a file-like object for the data that was
        sent with the request (e.g., the body of a POST request,
        or the documented uploaded in a PUT request).

        The file might not be rewound to the beginning if there
        was valid, form-encoded POST data.  Pass rewind=1 if
        you want to be sure you get the entire body of the request.
        """
        fs = self.fieldStorage()
        if rewind:
            fs.file.seek(0)
        return fs.file

    ## Information ##

    # @@ 2000-05-10: See FUTURE section of class doc string

    def servletPath(self):
        raise NotImplementedError

    def contextPath(self):
        raise NotImplementedError

    def pathInfo(self):
        raise NotImplementedError

    def pathTranslated(self):
        raise NotImplementedError

    def queryString(self):
        """
        Returns the query string portion of the URL for this
        request. Taken from the CGI variable QUERY_STRING. """
        return self._environ.get('QUERY_STRING', '')

    def uri(self):
        """
        Returns the request URI, which is the entire URL except
        for the query string. """
        return self._environ['REQUEST_URI']

    def method(self):
        """
        Returns the HTTP request method (in all uppercase), typically
        from the set GET, POST, PUT, DELETE, OPTIONS and TRACE."""
        return self._environ['REQUEST_METHOD'].upper()

    def sessionId(self):
        """ Returns a string with the session id specified by the
        client, or None if there isn't one. """
        sid = self.value('_SID_', None)
        return sid

    ## Inspection ##

    def info(self):
        raise NotImplementedError

    def htmlInfo(self):
        raise NotImplementedError
