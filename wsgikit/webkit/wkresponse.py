"""
A Webware HTTPResponse object.
"""

import time
from wkcommon import NoDefault, Cookie

class HTTPResponse(object):

    def __init__(self, transaction, environ, start_response):
        self._transaction = transaction
        self._environ = environ
        self._start_response = start_response
        self._writer = None
        self._committed = False
        self._autoFlush = False
        self.reset()
    
    def endTime(self):
        return self._endTime
    
    def recordEndTime(self):
        """
        Stores the current time as the end time of the response. This
        should be invoked at the end of deliver(). It may also be
        invoked by the application for those responses that never
        deliver due to an error."""
        self._endTime = time.time()

    ## Headers ##

    def header(self, name, default=NoDefault):
        """ Returns the value of the specified header. """
        if default is NoDefault:
            return self._headers[name.lower()]
        else:
            return self._headers.get(name.lower(), default)

    def hasHeader(self, name):
        return self._headers.has_key(name.lower())

    def setHeader(self, name, value):
        """
        Sets a specific header by name.
        """
        assert self._committed==0, "Headers have already been sent"
        self._headers[name.lower()] = value

    def headers(self):
        """
        Returns a dictionary-style object of all Header objects
        contained by this request. """
        return self._headers

    def clearHeaders(self):
        """
        Clears all the headers. You might consider a
        setHeader('Content-type', 'text/html') or something similar
        after this."""
        assert self._committed==0
        self._headers = {}

    ## Cookies ##

    def cookie(self, name):
        """ Returns the value of the specified cookie. """
        return self._cookies[name]

    def hasCookie(self, name):
        """
        Returns true if the specified cookie is present.
        """
        return self._cookies.has_key(name)
    
    def setCookie(self, name, value, path='/', expires='ONCLOSE',
              secure=False):
        """
        Set a cookie.  You can also set the path (which defaults to /),
        You can also set when it expires.  It can expire:
          'NOW': this is the same as trying to delete it, but it
            doesn't really seem to work in IE
          'ONCLOSE': the default behavior for cookies (expires when
                    the browser closes)
          'NEVER': some time in the far, far future.
          integer: a timestamp value
          tuple: a tuple, as created by the time module
        """
        cookie = Cookie(name, value)
        if expires == 'ONCLOSE' or not expires:
            pass # this is already default behavior
        elif expires == 'NOW' or expires == 'NEVER':
            t = time.gmtime(time.time())
            if expires == 'NEVER':
                t = (t[0] + 10,) + t[1:]
            t = time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", t)
            cookie.setExpires(t)
        else:
            t = expires
            if type(t) is StringType and t and t[0] == '+':
                interval = timeDecode(t[1:])
                t = time.time() + interval
            if type(t) in (IntType, LongType,FloatType):
                t = time.gmtime(t)
            if type(t) in (TupleType, TimeTupleType):
                t = time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", t)
            cookie.setExpires(t)
        if path:
            cookie.setPath(path)
        if secure:
            cookie.setSecure(secure)
        self.addCookie(cookie)

    def addCookie(self, cookie):
        """
        Adds a cookie that will be sent with this response.
        cookie is a Cookie object instance.  See WebKit.Cookie.
        """
        assert self._committed==0
        assert isinstance(cookie, Cookie)
        self._cookies[cookie.name()] = cookie

    def delCookie(self, name):
        """
        Deletes a cookie at the browser. To do so, one has
        to create and send to the browser a cookie with
        parameters that will cause the browser to delete it.
        """
        if self._cookies.has_key(name):
            self._cookies[name].delete()
        else:
            cookie = Cookie(name, None)
            cookie.delete()
            self.addCookie(cookie)
            
    def cookies(self):
        """
        Returns a dictionary-style object of all Cookie objects that will be sent
        with this response.
        """
        return self._cookies

    def clearCookies(self):
        """ Clears all the cookies. """
        assert self._committed==0
        self._cookies = {}

    ## Status ##

    def setStatus(self, code, msg=''):
        """ Set the status code of the response, such as 200, 'OK'. """
        assert self._committed==0, "Headers already sent."
        self.setHeader('Status', str(code) + ' ' + msg)

    ## Special responses ##

    def sendError(self, code, msg=''):
        """
        Sets the status code to the specified code and message.
        """
        assert self._committed==0, "Response already partially sent"
        self.setStatus(code, msg)

    def sendRedirect(self, url):
        """
        This method sets the headers and content for the redirect, but
        does NOT change the cookies. Use clearCookies() as
        appropriate.

        @@ 2002-03-21 ce: I thought cookies were ignored by user
        agents if a redirect occurred. We should verify and update
        code or docs as appropriate.
        """
        # ftp://ftp.isi.edu/in-notes/rfc2616.txt
        # Sections: 10.3.3 and others

        assert self._committed==0, "Headers already sent"

        self.setHeader('Status', '302 Redirect')
        self.setHeader('Location', url)
        self.setHeader('Content-type', 'text/html')

        self.write('<html> <body> This page has been redirected to '
                   '<a href="%s">%s</a>. </body> </html>' % (url, url))

    ## Output ##

    def write(self, charstr=None):
        """
        Write charstr to the response stream.
        """
        import pdb
        if not charstr:
            return
        if self._autoFlush:
            assert self._committed
            self._writer(charstr)
        else:
            self._output.append(charstr)

    def flush(self, autoFlush=True):
        """
        Send all accumulated response data now.  Commits the response
        headers and tells the underlying stream to flush.  if
        autoFlush is true, the responseStream will flush itself
        automatically from now on.
        """
        if not self._committed:
            self.commit()
        if self._output:
            self._writer(''.join(self._output))
        self._autoFlush = autoFlush

    def isCommitted(self):
        """
        Has the reponse already been partially or completely sent?  If
        this returns true, no new headers/cookies can be added to the
        response.
        """
        return self._committed

    def deliver(self):
        """
        The final step in the processing cycle.
        Not used for much with responseStreams added.
        """
        self.recordEndTime()
        if not self._committed: self.commit()

    def commit(self):
        """
        Write out all headers to the reponse stream, and tell the
        underlying response stream it can start sending data.
        """
        status = self._headers['status']
        del self._headers['status']
        headers = self._headers.items()
        for cookie in self._cookies.values():
            headers.append(('Set-Cookie', cookie.headerValue()))
        self._writer = self._start_response(status, headers)
        self._committed = True

    def wsgiIterator(self):
        return self._output

    def recordSession(self):
        raise NotImplementedError

    def reset(self):
        """
        Resets the response (such as headers, cookies and contents).
        """

        assert self._committed == 0
        self._headers = {}
        self.setHeader('Content-type','text/html')
        self.setHeader('Status', '200 OK')
        self._cookies = {}
        self._output = []

    def rawResponse(self):
        raise NotImplementedError

    def size(self):
        raise NotImplementedError

    def mergeTextHeaders(self, headerstr):
        raise NotImplementedError
