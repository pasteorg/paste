# By Peter Hunt
# The canonical location for this file: http://st0rm.hopto.org:8080/wsgi/

# new twisted.wsgi resource which uses the wsgiref library, available
# at http://cvs.eby-sarna.com/wsgiref/

from wsgiref import handlers

from twisted.web import resource, server, static
from twisted.internet import reactor
from twisted.python import log
from twisted import copyright

import string
import sys
import os
import time
import urllib
import types
# TODO: sendfile()!

class WSGIResource(resource.Resource):
    isLeaf = True
    def __init__(self, application, async=False):
        """
        application - WSGI application to host
        async - is the application guaranteed to NOT block?
        """
        resource.Resource.__init__(self)
        self.application = application
        self.async = async
    def render(self, request):
        TwistedHandler(self.application, request, self.async)
        return server.NOT_DONE_YET

class LogWrapper:
    def write(self, msg):
        log.err(msg)
    def flush(self):
        pass

log_wrapper = LogWrapper()        

class TwistedHandler(handlers.BaseHandler):
    origin_server = True
    server_software = server.version
    def __init__(self, application, request, async=False):
        self.request = request
        if async:
            self.run_async(application)
        else:
            reactor.callInThread(self.run, application)
    def async_finish_response(self):
        """Reads the next block of data yielded from the application generator, similar to finish_response except for async apps"""
        if not self.result_is_file() and not self.sendfile():
            if isinstance(self.result, types.GeneratorType):
                while True:
                    try:
                        data = self.result.next()
                        if len(data) == 0:
                            break # till next time folks!
                        else:
                            self._write(data)
                    except StopIteration:
                        self.close() # we're done
                        break
            else:
                self.finish_response()
        else:
            self.close()
    def _resume(self):
        reactor.callLater(0, self.async_finish_response)
    def run_async(self, application):
        try:
            self.setup_environ()
            self.environ["twisted.wsgi.resume"] = self._resume
            self.result = application(self.environ, self.start_response)
            self.async_finish_response()
        except:
            import traceback
            traceback.print_exc()
            try:
                self.handle_error()
            except:
                # If we get an error handling an error, just give up already!
                self.close()
                raise   # ...and let the actual server figure it out.
    def run(self, application):
        """Invoke the application synchronously"""
        # Note to self: don't move the close()!  Asynchronous servers shouldn't
        # call close() from finish_response(), so if you close() anywhere but
        # the double-error branch here, you'll break asynchronous servers by
        # prematurely closing.  Async servers must return from 'run()' without
        # closing if there might still be output to iterate over.
        try:
            self.setup_environ()
            self.result = application(self.environ, self.start_response)
            self.finish_response()
        except:
            try:
                self.handle_error()
            except:
                # If we get an error handling an error, just give up already!
                self.close()
                raise   # ...and let the actual server figure it out.
    def close(self):
        handlers.BaseHandler.close(self)
        self.request.finish()
    def send_headers(self):
        """OVERRIDE ME!"""
        self.cleanup_headers()
        self.headers_sent = True
        if self.client_is_modern():
            self.send_preamble()
            for (h,v) in self.headers.items():
                self.request.setHeader(h, v)
    def send_preamble(self):
        """Transmit version/status/date/server, via self._write()"""
        if self.client_is_modern():
            code,message = self.status.split(" ",1)
            self.request.setResponseCode(int(code), message)                                     
            if not self.headers.has_key('Date'):
                self.headers.add_header('Date', time.asctime(time.gmtime(time.time())))
            if self.server_software and not self.headers.has_key('Server'):
                self.headers.add_header('Server', self.server_software)
    def _write(self,data):
        """Override in subclass to buffer data for send to client

        It's okay if this method actually transmits the data; BaseHandler
        just separates write and flush operations for greater efficiency
        when the underlying system actually has such a distinction.
        """
        self.request.write(data)

    def _flush(self):
        """Override in subclass to force sending of recent '_write()' calls

        It's okay if this method is a no-op (i.e., if '_write()' actually
        sends the data.
        """
        # no-op
        #self.request.flush()

    def get_stdin(self):
        """Override in subclass to return suitable 'wsgi.input'"""
        self.request.content.seek(0)
        return self.request.content

    def get_stderr(self):
        """Override in subclass to return suitable 'wsgi.errors'"""
        return log_wrapper

    def add_cgi_vars(self):
        """Override in subclass to insert CGI variables in 'self.environ'"""
        script_name = "/"+string.join(self.request.prepath, '/')
        serverName = string.split(self.request.getRequestHostname(), ':')[0]
        if float(copyright.version[:3]) >= 1.3:
            port = str(self.request.getHost().port)
        else:
            port = str(self.request.getHost()[2])

        env = {"SERVER_SOFTWARE":   server.version,
               "SERVER_NAME":       serverName,
               "GATEWAY_INTERFACE": "CGI/1.1",
               "SERVER_PROTOCOL":   self.request.clientproto,
               "SERVER_PORT":       port,
               "REQUEST_METHOD":    self.request.method,
               "SCRIPT_NAME":       script_name, # XXX
               "SCRIPT_FILENAME":   "[wsgi application]",
               "REQUEST_URI":       self.request.uri,
               "SCRIPT_URI":        self.request.uri,
               "SCRIPT_URL":        self.request.path
        }

        client = self.request.getClient()
        if client is not None:
            env['REMOTE_HOST'] = client
        ip = self.request.getClientIP()
        if ip is not None:
            env['REMOTE_ADDR'] = ip
        pp = self.request.postpath
        if pp:
            env["PATH_INFO"] = "/"+string.join(pp, '/')

        qindex = string.find(self.request.uri, '?')
        if qindex != -1:
            qs = env['QUERY_STRING'] = self.request.uri[qindex+1:]
            if '=' in qs:
                qargs = []
            else:
                qargs = [urllib.unquote(x) for x in qs.split('+')]
        else:
            env['QUERY_STRING'] = ''
            qargs = []

        # Propogate HTTP headers
        for title, header in self.request.getAllHeaders().items():
            envname = string.upper(string.replace(title, '-', '_'))
            if title not in ('content-type', 'content-length'):
                envname = "HTTP_" + envname
            env[envname] = header
        # Propogate our environment
        # dont need to do this since we're updating old environ
        #for key, value in os.environ.items():
        #    if not env.has_key(key):
        #        env[key] = value
        self.environ.update(env)

# simple little delayed processing app
from twisted.internet import defer

def blocking_call():
    d = defer.Deferred()
    reactor.callLater(2, d.callback, None)
    return d

def phase2(result, environ):
    environ["thetime"] = time.time()
    environ["twisted.wsgi.resume"]()

def blocking_async_app(environ, start_response):
    write = start_response("200 OK", [("Content-type","text/plain")])
    yield "the time right now is " + `time.time()` + "\n"
    blocking_call().addCallback(phase2, environ)
    yield ""
    yield "the time now is " + `environ["thetime"]`

def serve_application(application, port=8080, async=False):
    resource = WSGIResource(application, async=async)
    reactor.listenTCP(port, server.Site(resource))
    reactor.run()

if __name__ == "__main__":
    import sys
    import optparse
    from paste.webkit.wsgiwebkit import webkit
    parser = optparse.OptionParser()
    parser.add_option('-p', '--port', dest='port',
                      default=8080, type='int',
                      help="Port to serve on (default 8080)")
    options, args = parser.parse_args()
    if not len(args) == 1:
        print "You must give one path, which is the root of your application"
        sys.exit(2)
    app = webkit(args[0])
    serve_application(app, port=options.port)

