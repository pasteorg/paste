__version__ = "0.0.5"

from threading import Thread, Event, currentThread, Lock
import socket, urllib
import token, tokenize
import re,sys, os
import types 
import json
      
    
class ObjectBuffer:
    def __init__(self):
        self.data=""
    
    def getObjects(self, data):
        self.data += data
        lines = [self.data]#.split("\n")
        def readline():
            try:
                return lines.pop(0) + "\n"
            except:
                return ""
        gen = tokenize.generate_tokens(readline)
        readCnt=0
        brCnt=0
        objects = []
        try:
            for (ttype, tstr, ps, pe, lne) in gen:
                if(ttype == token.ERRORTOKEN):
                    break
                elif ttype == token.OP:
                    if tstr == "{":
                        brCnt += 1
                    elif tstr == "}":
                        brCnt -= 1
                        if(brCnt==0):
                            s= self.data[readCnt:ps[1]+1]
                            objects.append(s)
                            readCnt += len(s)
        except:
            pass
        self.data = self.data[readCnt:]
        return objects

def getTracebackStr():
    import traceback
    import StringIO
    s=StringIO.StringIO("")
    traceback.print_exc(file=s)
    return s.getvalue()

NameAllowedRegExp=re.compile("^[a-zA-Z]\w*$")
def nameAllowed(name):
    """checks if a name is allowed.
    """
    if NameAllowedRegExp.match(name):
        return True
    else:
        return False
    
def getMethodByName(obj, name):
    """searches for an object with the name given inside the object given.
       "obj.child.meth" will return the meth obj.
    """
    try:#to get a method by asking the service
        obj = obj._getMethodByName(name)
    except:
        #assumed a childObject is ment 
        #split the name from objName.childObjName... -> [objName, childObjName, ...]
        #and get all objects up to the last in list with name checking from the service object
        names = name.split(".")
        for name in names:
            if nameAllowed(name):
                obj = getattr(obj, name)
    return obj                    

class PeerObject(object):
    """creates a peer object which will send requests to the remote service when invoked."""
    def __init__(self, name, conn):
        self._name = name
        self._conn = conn
        
    def __call__(self, *args):
        evt  = self._conn.sendRequest(self._name, args)
        return evt.waitForResponse()

    def __getattr__(self, name):
        return PeerObject(self._name + "." + name, self._conn)

class PeerNotifyObject(object):
    """same as PeerObject except that when called it will only send a notification"""
    def __init__(self, name, conn):
        self._name = name
        self._conn = conn
        
    def __call__(self, *args):
        self._conn.sendNotify(self._name, args)

    def __getattr__(self, name):
        return  PeerNotifyObject(self._name + "." + name, self._conn)
        

class Notify(object):
    def __init__(self, conn):
        self._conn = conn
    
    def __getattr__(self, name):
        return PeerNotifyObject(name, self._conn)
        
    def __call__(self, *args):
        evt  = self._conn.sendRequest("notify", args)
        return evt.waitForResponse()


class BasePeer(object):
    """Basic Peer class to create proxy services"""
    def __init__(self, conn):
        self._conn = conn
        self.notify = Notify(conn)
        
    def __getattr__(self, name):
        return PeerObject(name, self._conn)

        
   
class Request:
    def __init__(self, id, methodName, args):
        self.id = id
        self.methodName = methodName
        self.arguments = args
    def _toJSON(self):
        return '{"id":%s, "method":%s, "params":%s}' % (json.objToJson(self.id), json.objToJson(self.methodName), json.objToJson(self.arguments)) 

class Notification:
    def __init__(self, methodName, args):
        self.methodName = methodName
        self.arguments = args
    def _toJSON(self):
        return '{"method":%s, "params":%s}' % (json.objToJson(self.methodName), json.objToJson(self.arguments))

class Response:
    def __init__(self, id, result, error):
        self.id = id
        self.result = result
        self.error = error
    def _toJSON(self):
        return '{"id":%s, "result":%s, "error":%s}' % (json.objToJson(self.id), json.objToJson(self.result), json.objToJson(self.error))

class RPCLib:
    pass
        
class JSONRPCError:
    def __init__(self, msg=""):
        self.name = self.__class__.__name__
        self.msg = msg
    def _toJSON(self):
        s = objToJson(self.__dict__)
        return s
            
class InvalidMethodParameters(JSONRPCError):
    pass
    
class MethodNotFound(JSONRPCError):
    pass
    
class ApplicationError(JSONRPCError):
    pass



class Timeout(Exception):
    pass
    
class ResponseEvent:
    """Event which is fired when the response is returned for a request.
    
        For each request send this event is created. 
        An application can wait for the event to create a blocking request.
    """
    def __init__(self):
        self.__evt = Event()
        
    def waiting(self):
        return not self.__evt.isSet()
        
    def waitForResponse(self, timeOut=None):
        """blocks until the response arrived or timeout is reached."""
        self.__evt.wait(timeOut)
        if self.waiting():
            raise Timeout()
        else:
            if self.response.error:
                raise self.response.error
            else:
                return self.response.result
        
    def handleResponse(self, resp):
        self.response = resp
        self.__evt.set()
        

class BaseConnectionHandler(object):
    """The basic connection handler.
        
       It handles the data connection between a local service and a single remote peer.
    """
    def __init__(self, service, PeerClass=BasePeer):
        self.buffer=ObjectBuffer()
        self.service = service
        self.respEvents = {}
        self.peer = PeerClass(self)
        self.parser = json.JSONParser()
        self.parser.addLib(RPCLib(), "rpc", [])
        service._registerPeer(self.peer)
        self.respLock = Lock()
        
    def recv(self):
        pass
        
    def send(self, data):
        pass
    
    def close(self):
        try:
            self.service._unregisterPeer(self.peer)
        except:
            pass
        
    def newResponseEvent(self):
        """creates a response event and adds it to a waiting list
           When the reponse arrives it will be removed from the list. 
        """
        respEvt = ResponseEvent()
        self.respLock.acquire()
        i=1
        keys = self.respEvents.keys()
        while "%d" % i in keys:
            i+=1
        id="%d" % i
        self.respEvents[id] = respEvt
        self.respLock.release()
        return (respEvt,id)
        
    def sendNotify(self, name, args):
        """sends a notification object to the peer"""
        self.send(self.parser.objToJson(Notification(name, args)))
        
    def sendRequest(self, name, args):
        """sends a request to the peer"""
        (respEvt, id) = self.newResponseEvent()
        self.send(self.parser.objToJson(Request(id,name, args)))
        return respEvt
        
    def sendResponse(self, id, result, error):
        """sends a response to the peer"""
        self.send(self.parser.objToJson(Response(id, result, error)))
     
    def handleRequest(self, req):
        """handles a request by calling the appropriete method the service exposes"""
        name = req["method"]
        params = req["params"]
        id=req["id"]
        try: #to get a callable obj 
            obj = getMethodByName(self.service, name)
        except:
            obj=None
            self.sendResponse(id, None, MethodNotFound(name))
        if obj:
            try: #to call the object with parameters
                rslt = obj(*params)
                self.sendResponse(id, rslt, None)
            except TypeError: # wrong arguments
                #todo what if the TypeError was not thrown directly by the callable obj
                self.sendResponse(id, None, InvalidMethodParameters())
            except: #error inside the callable object
                s=getTracebackStr()
                self.sendResponse(id, None, ApplicationError(s))
                
    def handleNotification(self, req):
        """handles a notification request by calling the appropriete method the service exposes"""
        name = req["method"]
        params = req["params"]
        try: #to get a callable obj 
            obj = getMethodByName(self.service, name)
            rslt = obj(*params)
        except:
            pass
                
    def handleResponse(self, resp):
        """handles a response by fireing the response event for the response coming in"""
        id=resp["id"]
        evt = self.respEvents[id]
        del(self.respEvents[id])
        evt.handleResponse(resp)
    
    def handleData(self, data):
        """handles incomming data"""
        objs = self.buffer.getObjects(data)
        for objData in objs:
            try:
                obj = self.parser.jsonToObj(objData)
            except:
                raise "Not well formed."
            if obj.has_key("method") and obj.has_key("params"):
                if obj.has_key("id"):
                    if obj["id"]:
                        self.handleRequest(obj)    
                    else:
                        self.handleNotification(obj)
                else:
                    self.handleNotification(obj)
            elif obj.has_key("result") and obj.has_key("error"):
                self.handleResponse(obj)
            else:#unknown object 
                raise "Unknown data"
                
class RequestThread(Thread):
    def __init__(self, connection, request):
        Thread.__init__(self)
        self.setDaemon(True)
        self.connection = connection
        self.peer = connection.peer
        self.request = request
    def run(self):
        self.connection.handleRequestThread(self.request)
    
class ThreadedConnectionHandler(BaseConnectionHandler, Thread):
    def __init__(self, service, PeerClass=BasePeer):
        Thread.__init__(self)
        self.setDaemon(True)
        BaseConnectionHandler.__init__(self, service, PeerClass)
        
    def handleRequestThread(self, req):
        BaseConnectionHandler.handleRequest(self, req)
        
    def handleRequest(self, req):
        RequestThread(self, req).start()
    
    def run(self):
        dorun = True
        while dorun:
            data = self.recv()
            if data =="":
                dorun=False
                self.close()
            else:
                self.handleData(data)
        
                
    
class SocketConnectionHandler(ThreadedConnectionHandler):
    def __init__(self, socket, service, PeerClass=BasePeer):
        self.socket = socket
        ThreadedConnectionHandler.__init__(self, service, PeerClass)
        
    def recv(self):
        try:
            s = self.socket.recv(1024)
        except:
            s = ""
        return s
        
    def send(self, data):
        self.socket.send(data)
    
    def close(self):
        BaseConnectionHandler.close(self)
        try:
            self.socket.close()
        except:
            pass


class CGIConnectionHandler(BaseConnectionHandler):
    def __init__(self, service, PeerClass=BasePeer):
        BaseConnectionHandler.__init__(self, service, PeerClass)
        self.replied = False
        
    def send(self, data):
        self.replied = True
        response = "Content-Type: text/plain\n"
        response += "Content-Length: %d\n\n" % len(data)
        response += data
        
        #on windows all \n are converted to \r\n if stdout is a terminal and  is not set to binary mode :(
        #this will then cause an incorrect Content-length.
        #I have only experienced this problem with apache on Win so far.
        if sys.platform == "win32":
            import  msvcrt
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        #put out the response
        sys.stdout.write(response)
        
    def handle(self):
        try:
            contLen=int(os.environ['CONTENT_LENGTH'])
            data = sys.stdin.read(contLen)
            #execute the request
            self.handleData(data) 
        except:
            self.sendResponse(None, None, "Not a JSON-RPC post")
        self.close()
    
    def close(self):
        if not self.replied:
            self.send("")
        BaseConnectionHandler.close(self)

class HTTPResponseEvent:
    def __init__(self, result, error):
        self.error = error
        self.result = result
        
    def waitForResponse(self):
        if self.error:
            raise self.error
        else:
            return self.result
        
class HTTPConnectionHandler(BaseConnectionHandler):
    def __init__(self, url, service, PeerClass=BasePeer):
        self.url = url
        BaseConnectionHandler.__init__(self, service, PeerClass)
    
    def sendNotify(self, name, args):
        urllib.urlopen(self.url, self.parser.objToJson(Notification(name, args)))
        
    def sendRequest(self, name, args):
        data = self.parser.objToJson(Request(1, name, args))
        resp = urllib.urlopen(self.url, data)
        data = resp.read()
        try:
            obj = self.parser.jsonToObj(data)
        except:
            return HTTPResponseEvent(None, "Data received is not well formed.")
            
        if obj.has_key("result"):
            if(obj["error"]):
                return HTTPResponseEvent(None, obj["error"])
            else:
                return HTTPResponseEvent(obj["result"], None)
        else:
            return HTTPResponseEvent(None, "Bad Data")
        
    
class Service:
    def __init__(self):
        self._peers = []
        
    def _registerPeer(self, peer):
        self._peers.append(peer)
    
    def _unregisterPeer(self, peer):
        self._peers.remove(peer)
    
    def _isCurrentPeer(self, peer):
        try:
            return currentThread().peer == peer
        except:
            return False;
        
class ServiceServer:
    def __init__(self, service, ConnectionHandler):
        self.service = service
        self.ConnectionHandler = ConnectionHandler
        
    def run(self):
        while 1:
            conn = self.accept()
            self.handleConnection(conn)
            
    def handleConnection(self, conn):
        self.ConnectionHandler(conn, self.service).start()
    
    
class TCPServiceServer(ServiceServer):
    def __init__(self, address, service, ConnectionHandler=SocketConnectionHandler):
        ServiceServer.__init__(self, service, ConnectionHandler)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(address)        
        self.socket.listen(5)
        
    def accept(self):
        return self.socket.accept()[0]
      

class ServiceProxy(BasePeer):
    def __init__(self, url, service=Service()):
        m = re.match(r"^jsonrpc:\/\/(.*):(\d*)$", url)
        if m:
            (host, port)= m.groups();
            port = int(port)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            conn = SocketConnectionHandler(s, service)
            conn.start()
        else:
            conn = HTTPConnectionHandler(url, service)
        BasePeer.__init__(self, conn)
        
    


