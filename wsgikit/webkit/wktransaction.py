"""
The Webware transaction object.  Responsible for creating the request
and response objects, and managing some parts of the request cycle.
"""

from wkrequest import HTTPRequest
from wkresponse import HTTPResponse
from wksession import Session
from wkapplication import Application

class Transaction(object):

    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response
        self._request = HTTPRequest(self, environ)
        self._response = HTTPResponse(self, environ, start_response)
        self._session = None
        self._application = None

    def application(self):
        if self._application is None:
            self._application = Application(self)
        return self._application

    def request(self):
        return self._request

    def response(self):
        return self._response

    def setResponse(self, response):
        assert 0, "The response cannot be set"

    def hasSession(self):
        return self._session is not None

    def session(self):
        if not self._session:
            self._session = Session(self.request().environ()['wsgikit.session.factory']())
        return self._session

    def setSession(self, session):
        self._session = session

    def servlet(self):
        return self._servlet

    def setServlet(self, servlet):
        self._servlet = servlet

    def duration(self):
        return self.response().endTime() - self.request().time()

    def errorOccurred(self):
        assert 0, "Not tracked"

    def setErrorOccurred(self, flag):
        assert 0, "Not tracked"

    def awake(self):
        if self._session:
            self._session.awake(self)
        self._servlet.awake(self)

    def respond(self):
        self._servlet.respond(self)

    def sleep(self):
        self._servlet.sleep(self)

    def die(self):
        # In WebKit this looks for any instance variables with a
        # resetKeyBindings method, but I'm not sure why
        pass

    def writeExceptionReport(self, handler):
        assert 0, "Not implemented"

    def runTransaction(self):
        try:
            self.awake()
            self.respond()
        finally:
            self.sleep()

    def forward(self, url):
        assert self._environ.has_key('wsgikit.recursive.forward'), \
               "Forwarding is not supported (use the recursive middleware)"
        if url.startswith('/'):
            # Webware considers absolute paths to still be based off
            # of the Webware root; but recursive does not.
            url = url[1:]
        app_iter = self._environ['wsgikit.recursive.forward'](url)
        raise self._servlet.ReturnIterException(app_iter)
    
