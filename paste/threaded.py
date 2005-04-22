# Note, this is totally incomplete and untested
import threading
import marshal
import Queue
import select
import socket
import errno
import logging
import atexit
import BaseHTTPServer

__version__ = '0.1'

logger = logging.getLogger('wsgiserver.threaded')
errorLog = logging.getLogger('wsgiserver.apperrors')

intLength = len(marshal.dumps(int(1)))

server = None

class NotEnoughDataError(Exception):
    pass

class ProtocolError(Exception):
    pass

class ThreadedWSGIServer(object):

    def __init__(self, application):
        self.application = application
        threadCount = self.setting('StartServerThreads')
        self._maxServerThreads = self.setting('MaxServerThreads')
        self._minServerThreads = self.setting('MinServerThreads')
        self._threadPool = []
        self._threadCount = 0
        self._threadUseCounter = []
        self._requestQueue = Queue.Queue(self._maxServerThreads * 2)
        self._addr = {}
        # @@: Should load persistently
        self._requestID = 0
        
        logger.info('Creating %i threads' % threadCount)
        for i in range(threadCount):
            self.spawnThread()

        #self.recordPID() @@: ?

        self._socketHandlers = {}
        self._handlerCache = {}
        self._sockets = {}

        self.addSocketHandlers()
        self.running = True
        atexit.register(self.awakeSelect)
        atexit.register(self.shutdown)
        self.readyForRequests()

    def addSocketHandler(self, handlerClass, serverAddress=None):
        """
        Adds a socket handler for `serverAddress`, which is typically
        a tuple ``(host, port)``.
        """
        if serverAddress is None:
            serverAddress = self.address(handlerClass.defaultServerAddress())
        self._socketHandlers[serverAddress] = handlerClass
        self._handlerCache[serverAddress] = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(serverAddress)
        sock.listen(1024)
        self._sockets[serverAddress] = sock
        logger.info('Listening on: %s' % serverAddress)

    def readyForRequests(self):
        logger.info('Ready for requests')

    def spawnThread(self):
        """
        Create a new worker thread; threads run the `threadLoop`
        method.
        """
        t = threading.Thread(target=self.threadLoop)
        t.processing = False
        self._threadPool.append(t)
        self._threadCount += 1
        t.start()
        logger.info('New thread spawned, threadcount=%s' %
                    self._threadCount)

    def absorbThread(self, count=1):
        """
        Absorb a thread.
        """
        for i in range(count):
            self._requestQueue.put(None)
            self._threadCount -= 1
        for t in self._threadPool:
            if not t.isAlive():
                rv = i.join()
                self._threadPool.remove(i)
                logger.info('Thread absorbed, threadcount=%s' %
                            len(self.threadPool))

    def threadLoop(self):
        self.initThread()
        t = threading.currentThread()
        t.processing = False
        try:
            while 1:
                try:
                    handler = self._requestQueue.get()
                    # Non means time to quit
                    if handler is None:
                        break
                    t.processing = True
                    try:
                        handler.handleRequest()
                    except:
                        logger.exception()
                    handler.close()
                    t.processing = False
                except Queue.Empty:
                    pass
        finally:
            self.delThread()

    def initThread(self):
        pass

    def delThread(self):
        pass

    def awakeSelect(self):
        """
        The ``select()`` in `mainloop` is blocking, so when
        we shut down we have to make a connect to unblock it.
        Here's where we do that, called `shutDown`.
        """

        for addr in self._sockets.keys():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect(addr)
                sock.close()
            except:
                pass

    def shutdown(self):
        self.running = False
    
    def run(self, timeout=1):
        while 1:
            if not self.running:
                return

            try:
                input, output, exc = select.select(
                    self._sockets.values(), [], [], timeout)
            except select.error, v:
                if v[0] == errno.EINTR or v[0] == 0:
                    break
                else:
                    raise

            for sock in input:
                self._requestID += 1
                client, addr = sock.accept()
                serverAddress = sock.getsockname()
                try:
                    handler = self._handlerCache[serverAddress].pop()
                except IndexError:
                    handler = self._socketHandlers[serverAddress](self, serverAddress)
                handler.activate(client, self._requestID)
                self._requestQueue.put(handler)

class Handler(object):

    def __init__(self, server, serverAddress):
        self.server = server
        self.serverAddress = serverAddress

    def active(self, sock, requestID):
        self.requestID = requestID
        self.sock = sock

    def close(self):
        self.sock = None
        self.server._handlerCache[self._serverAddress].append(self)

    def handleRequest(self):
        raise NotImplementedError

class ModWebKitHandler(Handler):

    protocolName = 'webkit'
    
    def receiveDict(self):
        """
        Utility function to receive a marshalled dictionary from
        the socket.  Returns None if the request was empty.
        """
        chunk = ''
        missing = intLength
        while missing > 0:
            block = self.sock.recv(missing)
            if not block:
                self.sock.close()
                if len(chunk) == 0:
                    # We probably awakened due to awakeSelect being called.
                    return None
                else:
                    # We got a partial request -- something went wrong.
                    raise NotEnoughDataError, 'received only %d of %d bytes when receiving dictLength' % (len(chunk), intLength)
            chunk += block
            missing = intLength - len(chunk)
        try:
            dictLength = loads(chunk)
        except ValueError:
            logger.warn('bad marshal data for webkit adapter interface; '
                        'you can only connect to %s via an adapter, like '
                        'mod_webkit or wkcgi, not with a browser'
                        % self._serverAddress[1])
            raise
        if type(dictLength) != type(1):
            self.sock.close()
            raise ProtocolError, "Invalid AppServer protocol"
        chunk = ''
        missing = dictLength
        while missing > 0:
            block = self.sock.recv(missing)
            if not block:
                self.sock.close()
                raise NotEnoughDataError, 'received only %d of %d bytes when receiving dict' % (len(chunk), dictLength)
            chunk += block
            missing = dictLength - len(chunk)
        return loads(chunk)

    def defaultServerAddress(cls):
        return ('127.0.0.1', 8086)
    defaultServerAddress = classmethod(defaultServerAddress)

    def handleRequest(self):
        data = []
        environ = self.receiveDict()
        if not environ:
            return
        if environ.get('REQUEST_URI'):
            requestURI = environ['REQUEST_URI']
        else:
            requestURI = environ.get('SCRIPT_NAME', '') + environ.get('PATH_INFO', '')
            query = environ.get('QUERY_STRING')
            if query:
                requestURI += '?' + query
        environ['wsgi.input'] = self.sock.makefile('rb', 8012)
        environ['wsgi.errors'] = LoggingError(errorLog)
        environ['wsgi.version'] = '1.0'
        environ['wsgi.multithread'] = True
        environ['wsgi.multiprocess'] = False
        output = WebKitStreamOut(self.sock)

        def start(status, headers):
            output.write('Status: %s\n' % status)
            for header, value in headers.items():
                assert '\n' not in value and '\r' not in value, \
                       "Headers cannot contain newlines (%s: %r)" \
                       % (header, value)
                assert ':' not in header, \
                       "Headers should not container ':' (%r)" % header
                output.write('%s: %s\n' % (key, value))
            return output.write

        try:
            result = self.server.application(environ, start)
            if result:
                try:
                    for data in result:
                        output.write(data)
                finally:
                    if hasattr(result, 'close'):
                        result.close()
        except:
            errorLog.exception()

        output.close()
        try:
            self.sock.shutdown(1)
            self.sock.close()
        except:
            # @@: Why the except:?
            pass
        
class LoggingError(object):

    def __init__(self, logger):
        self.logger = logger

    def flush(self):
        pass

    def write(self, s):
        self.logger.error(s)

    def writelines(self, seq):
        for s in seq:
            self.write(s)

class WebKitStreamOut(object):

    def __init__(self, sock):
        self.sock = sock

    def write(self, s):
        self.sock.send(s)

############################################################
## HTTP
############################################################


class HTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Handles incoming requests.  Recreated with every request.
    Abstract base class.
    """

    ## This sends certain CGI variables.  These are some that
    ## should be sent, but aren't:
    ## SERVER_ADDR
    ## SERVER_PORT
    ## SERVER_SOFTWARE
    ## SERVER_NAME
    ## HTTP_CONNECTION
    ## SERVER_PROTOCOL
    ## HTTP_KEEP_ALIVE

    ## These I don't think are needed:
    ## DOCUMENT_ROOT
    ## PATH_TRANSLATED
    ## GATEWAY_INTERFACE
    ## PATH
    ## SERVER_SIGNATURE
    ## SCRIPT_FILENAME (?)
    ## SERVER_ADMIN (?)

    server_version = 'WSGIServer/%s' % __version__

    def handleRequest(self):
        """
        Actually performs the request, creating the environment and
        calling self.doTransaction(env, myInput) to perform the
        response.
        """
        self.server_version = 'Webware/0.1'
        env = {}
        if self.headers.has_key('Content-Type'):
            env['CONTENT_TYPE'] = self.headers['Content-Type']
            del self.headers['Content-Type']
        self.headersToEnviron(self.headers, env)
        env['REMOTE_ADDR'], env['REMOTE_PORT'] = map(str, self.client_address)
        env['REQUEST_METHOD'] = self.command
        path = self.path
        if path.find('?') != -1:
            # @@: should REQUEST_URI include QUERY_STRING?
            env['REQUEST_URI'], env['QUERY_STRING'] = path.split('?', 1)
        else:
            env['REQUEST_URI'] = path
            env['QUERY_STRING'] = ''
        env['PATH_INFO'] = env['REQUEST_URI']
        env['SCRIPT_NAME'] = ''
        myInput = ''
        if self.headers.has_key('Content-Length'):
            myInput = self.rfile.read(int(self.headers['Content-Length']))
        self.doTransaction(env, myInput)

    do_GET = do_POST = do_HEAD = handleRequest
    # These methods are used in WebDAV requests:
    do_OPTIONS = do_PUT = do_DELETE = handleRequest
    do_MKCOL = do_COPY = do_MOVE = handleRequest
    do_PROPFIND = handleRequest

    def headersToEnviron(self, headers, env):
        """Use a simple heuristic to convert all the headers to
        environmental variables..."""
        for header, value in headers.items():
            env['HTTP_%s' % (header.upper().replace('-', '_'))] = value
        return env

    def processResponse(self, data):
        """
        Takes a string (like what a CGI script would print) and
        sends the actual HTTP response (response code, headers, body).
        """
        s = StringIO(data)
        headers = mimetools.Message(s)
        self.sendStatus(headers)
        self.sendHeaders(headers)
        self.sendBody(s)

    def sendStatus(self, status):
        status = str(status)
        pos = status.find(' ')
        if pos == -1:
            code = int(status)
            message = ''
        else:
            code = int(status[:pos])
            message = status[pos:].strip()
        self.send_response(code, message)

    def sendHeaders(self, headers):
        for header, value in headers.items():
            self.send_header(header, value)
        self.end_headers()

    def sendBody(self, bodyFile):
        self.wfile.write(bodyFile.read())
        bodyFile.close()

    def log_message(self, format, *args):
        self.server.logMessage(format % args)

    def log_request(self, *args, **kw):
        pass


class HTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    protocolName = 'http'

    def defaultServerAddress(cls):
        # @@: 127.0.0.1 isn't very useful
        return ('127.0.0.1', 80)
    defaultServerAddress = classmethod(defaultServerAddress)

    def handleRequest(self):
        baseHandler = BaseHTTPHandler(req, None, self)
        
