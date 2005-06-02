"""
This implements all of the Webware servlets (Servlet, HTTPServlet, and
Page), as WSGI applications.  The servlets themselves are
applications, and __call__ is provided to do this.
"""

import wkcommon
from wktransaction import Transaction

class make_application(object):

    def __get__(self, obj, type=None):
        # Instances are already applications:
        if obj:
            return obj
        # This application creates an instance for each call:
        def application(environ, start_response):
            return type()(environ, start_response)
        return application

class Servlet(object):

    # This is nested in Servlet so that transactions can access it as
    # an attribute, instead of having to import this module.  (If they
    # had to import this module, there would be a circular import)
    # @@: Why not just put this in wktransaction?
    class ReturnIterException(Exception):
        def __init__(self, app_iter):
            self.app_iter = app_iter
    
    def __call__(self, environ, start_response):
        """
        The core WSGI method, and the core of the servlet execution.
        """
        __traceback_hide__ = 'before_and_this'
        trans = Transaction(environ, start_response)
        trans.setServlet(self)
        try:
            trans.runTransaction()
            trans.response().deliver()
            return trans.response().wsgiIterator()
        except self.ReturnIterException, e:
            return e.app_iter
        except self.EndResponse:
            trans.response().deliver()
            return trans.response().wsgiIterator()

    wsgi_app = make_application()
    
    ## Access ##

    def name(self):
        """
        Returns the name which is simple the name of the
        class. Subclasses should *not* override this method. It is
        used for logging and debugging. """
        return self.__class__.__name__


    def awake(self, trans):
        """
        This message is sent to all objects that participate in the
        request-response cycle in a top-down fashion, prior to
        respond(). Subclasses must invoke super.
        """
        self._transaction = trans

    def respond(self, trans):
        raise AbstractError, self.__class__

    def sleep(self, trans):
        pass

    ## Abilities ##

    def canBeThreaded(self):
        """ Returns 0 or 1 to indicate if the servlet can be
        multithreaded. This value should not change during the
        lifetime of the object. The default implementation returns
        0. Note: This is not currently used. """
        return 0

    def canBeReused(self):
        """ Returns 0 or 1 to indicate if a single servlet instance
        can be reused. The default is 1, but subclasses con override
        to return 0. Keep in mind that performance may seriously be
        degraded if instances can't be reused. Also, there's no known
        good reasons not to reuse and instance. Remember the awake()
        and sleep() methods are invoked for every transaction. But
        just in case, your servlet can refuse to be reused. """
        return 1

class HTTPServlet(Servlet):

    def __init__(self):
        Servlet.__init__(self)
        self._methodForRequestType = {}  # a cache; see respond()

    ## From WebKit.HTTPServlet ##

    def respond(self, trans):
        """
        Invokes the appropriate respondToSomething() method
        depending on the type of request (e.g., GET, POST, PUT,
        ...). """
        httpMethodName = trans.request().method()
        method = self._methodForRequestType.get(httpMethodName, None)
        if not method:
            methName = 'respondTo' + httpMethodName.capitalize()
            method = getattr(self, methName, self.notImplemented)
            self._methodForRequestType[httpMethodName] = method
        method(trans)

    def notImplemented(self, trans):
        trans.response().setHeader('Status', '501 Not Implemented')

    def respondToHead(self, trans):
        """
        A correct but inefficient implementation.
        Should at least provide Last-Modified and Content-Length.
        """
        res = trans.response()
        w = res.write
        res.write = lambda *args: None
        self.respondToGet(trans)
        res.write = w

class Page(HTTPServlet):

    class EndResponse(Exception):
        pass

    ## Server side filesystem ##

    def serverSidePath(self, path=None):
        raise NotImplementedError

    ## From WebKit.Page ##

    def awake(self, transaction):
        self._transaction = transaction
        self._response    = transaction.response()
        self._request     = transaction.request()
        self._session     = None  # don't create unless needed
        assert self._transaction is not None
        assert self._response    is not None
        assert self._request     is not None

    def respondToGet(self, transaction):
        """ Invokes _respond() to handle the transaction. """
        self._respond(transaction)

    def respondToPost(self, transaction):
        """ Invokes _respond() to handle the transaction. """
        self._respond(transaction)

    def _respond(self, transaction):
        """
        Handles actions if an _action_ field is defined, otherwise
        invokes writeHTML().
        Invoked by both respondToGet() and respondToPost().
        """
        req = transaction.request()

        # Check for actions
        for action in self.actions():
            if req.hasField('_action_%s' % action) or \
               req.field('_action_', None) == action or \
               (req.hasField('_action_%s.x' % action) and \
                req.hasField('_action_%s.y' % action)):
                if self._actionSet().has_key(action):
                    self.handleAction(action)
                    return

        self.writeHTML()

    def sleep(self, transaction):
        self._session = None
        self._request  = None
        self._response = None
        self._transaction = None

    ## Access ##

    def application(self):
        return self.transaction().application()

    def transaction(self):
        return self._transaction

    def request(self):
        return self._request

    def response(self):
        return self._response

    def session(self):
        if not self._session:
            self._session = self._transaction.session()
        return self._session


    ## Generating results ##

    def title(self):
        """ Subclasses often override this method to provide a custom title. This title should be absent of HTML tags. This implementation returns the name of the class, which is sometimes appropriate and at least informative. """
        return self.__class__.__name__

    def htTitle(self):
        """ Return self.title(). Subclasses sometimes override this to provide an HTML enhanced version of the title. This is the method that should be used when including the page title in the actual page contents. """
        return self.title()

    def htBodyArgs(self):
        """
        Returns the arguments used for the HTML <body> tag. Invoked by
        writeBody().

        With the prevalence of stylesheets (CSS), you can probably skip
        this particular HTML feature.
        """
        return 'color=black bgcolor=white'

    def writeHTML(self):
        """
        Writes all the HTML for the page.

        Subclasses may override this method (which is invoked by
        respondToGet() and respondToPost()) or more commonly its
        constituent methods, writeDocType(), writeHead() and
        writeBody().
        """
        self.writeDocType()
        self.writeln('<html>')
        self.writeHead()
        self.writeBody()
        self.writeln('</html>')

    def writeDocType(self):
        """
        Invoked by writeHTML() to write the <!DOCTYPE ...> tag.

        @@ sgd-2003-01-29 - restored the 4.01 transitional as per discussions
        on the mailing list for the 0.8 release.

        # This implementation USED TO specify HTML 4.01 Transitional, but
        # some versions of Mozilla acted strangely with that. The current
        # implementation does nothing.

        Subclasses may override to specify something else.

        You can find out more about doc types by searching for DOCTYPE
        on the web, or visiting:
            http://www.htmlhelp.com/tools/validator/doctype.html
        """
        self.writeln('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">')
        pass

    def writeHead(self):
        """
        Writes the <head> portion of the page by writing the
        <head>...</head> tags and invoking writeHeadParts() in between.
        """
        wr = self.writeln
        wr('<head>')
        self.writeHeadParts()
        wr('</head>')

    def writeHeadParts(self):
        """
        Writes the parts inside the <head>...</head> tags. Invokes
        writeTitle() and writeStyleSheet(). Subclasses can override this
        to add additional items and should invoke super.
        """
        self.writeTitle()
        self.writeStyleSheet()

    def writeTitle(self):
        """
        Writes the <title> portion of the page. Uses title().
        """
        self.writeln('\t<title>%s</title>' % self.title())

    def writeStyleSheet(self):
        """
        Writes the style sheet for the page, however, this default
        implementation does nothing. Subclasses should override if
        necessary. A typical implementation is:
            self.writeln('\t<link rel=stylesheet href=StyleSheet.css type=text/css>')
        """
        pass

    def writeBody(self):
        """
        Writes the <body> portion of the page by writing the
        <body>...</body> (making use of self.htBodyArgs()) and invoking
        self.writeBodyParts() in between.
        """
        wr = self.writeln
        bodyArgs = self.htBodyArgs()
        if bodyArgs:
            wr('<body %s>' % bodyArgs)
        else:
            wr('<body>')
        self.writeBodyParts()
        wr('</body>')

    def writeBodyParts(self):
        """
        Invokes writeContent(). Subclasses should only override this
        method to provide additional page parts such as a header,
        sidebar and footer, that a subclass doesn't normally have to
        worry about writing.

        For writing page-specific content, subclasses should override
        writeContent() instead.

        See SidebarPage for an example override of this method.

        Invoked by writeBody().
        """
        self.writeContent()

    def writeContent(self):
        """
        Writes the unique, central content for the page.

        Subclasses should override this method (not invoking super) to
        write their unique page content.

        Invoked by writeBodyParts().
        """
        self.writeln('<p> This page has not yet customized its content. </p>')


    ## Writing ##

    def write(self, *args):
        for arg in args:
            self._response.write(str(arg))

    def writeln(self, *args):
        for arg in args:
            self._response.write(str(arg))
        self._response.write('\n')


    ## Threading ##

    def canBeThreaded(self):
        """ Returns 0 because of the ivars we set up in awake(). """
        return 0


    ## Actions ##

    def handleAction(self, action):
        """
        Invoked by `_respond` when a legitimate action has
        been found in a form. Invokes `preAction`, the actual
        action method and `postAction`.
        
        Subclasses rarely override this method.
        """
        self.preAction(action)
        getattr(self, action)()
        self.postAction(action)

    def actions(self):
        return []

    def preAction(self, actionName):
        raise NotImplementedError

    def postAction(self, actionName):
        raise NotImplementedError

    def methodNameForAction(self, name):
        raise NotImplementedError

    ## Convenience ##

    def htmlEncode(self, s):
        return wkcommon.htmlEncode(s)

    def htmlDecode(self, s):
        return wkcommon.htmlDecode(s)

    def urlEncode(self, s):
        return wkcommon.urlEncode(s)

    def urlDecode(self, s):
        return wkcommon.urlDecode(s)

    def forward(self, URL):
        self.application().forward(self.transaction(), URL)

    def includeURL(self, URL):
        raise NotImplementedError

    def callMethodOfServlet(self, URL, method, *args, **kwargs):
        raise NotImplementedError

    def endResponse(self):
        raise self.EndResponse()

    def sendRedirectAndEnd(self, url):
        """
        Sends a redirect back to the client and ends the response. This
        is a very popular pattern.
        """
        self.response().sendRedirect(url)
        self.endResponse()


    ## Self utility ##

    def sessionEncode(self, url=None):
        """
        Utility function to access session.sessionEncode.
        Takes a url and adds the session ID as a parameter.  This is for cases where
        you don't know if the client will accepts cookies.
        """
        if url == None:
            url = self.request().uri()
        return self.session().sessionEncode(url)


    ## Private utility ##

    def _actionSet(self):
        """ Returns a dictionary whose keys are the names returned by actions(). The dictionary is used for a quick set-membership-test in self._respond. Subclasses don't generally override this method or invoke it. """
        if not hasattr(self, '_actionDict'):
            self._actionDict = {}
            for action in self.actions():
                self._actionDict[action] = 1
        return self._actionDict


    ## Validate HTML output (developer debugging) ##

    def validateHTML(self, closingTags='</body></html>'):
        raise NotImplementedError


