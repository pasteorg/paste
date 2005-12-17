# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
Cookie "Saved" Authentication

This Authentication middleware saves the current REMOTE_USER, and any
other environment variables specified, in a cookie so that it can be
retrieved during the next request without requiring re-authentication.
This uses a session cookie on the client side (so it goes away when the
user closes their window) and does server-side expiration.

  NOTE: If you use HTTPFound or other redirections; it is likely that
        this module will not work unless it is _before_ the middleware
        that converts the exception into a response.  Therefore, in your
        component stack, put this component darn near the top (before
        the exception handler).

According to the cookie specifications, RFC2068 and RFC2109, browsers
should allow each domain at least 20 cookies; each one with a content
size of at least 4k (4096 bytes).  This is rather small; so one should
be parsimonious in your cookie name/sizes.
"""
import sha, hmac, base64, random, time, string, warnings
from paste.request import get_cookies

def make_time(value):
    """ return a human readable timestmp """
    return time.strftime("%Y%m%d%H%M",time.gmtime(value))
_signature_size = len(hmac.new('x','x',sha).digest())
_header_size = _signature_size + len(make_time(time.time()))

# build encode/decode functions to safely pack away values
_encode = [('\\','\\x5c'),('"','\\x22'),('=','\\x3d'),(';','\\x3b')]
_decode = [(v,k) for (k,v) in _encode]
_decode.reverse()
def encode(s, sublist = _encode):
    return reduce((lambda a,(b,c): string.replace(a,b,c)), sublist, str(s))
decode = lambda s: encode(s,_decode)

class CookieTooLarge(RuntimeError):
    def __init__(self, content, cookie):
        RuntimeError.__init__("Signed cookie exceeds maximum size of 4096")
        self.content = content
        self.cookie = cookie

class CookieSigner:
    """
    This class converts content into a timed and digitally signed
    cookie, as well as having the facility to reverse this procedure. 
    If the cookie, after the content is encoded and signed exceeds the
    maximum length (4096), then CookieTooLarge exception is raised.

    The timeout of the cookie is handled on the server side for a few
    reasons.  First, if a 'Expires' directive is added to a cookie, then
    the cookie becomes persistent (lasting even after the browser window
    has closed). Second, the user's clock may be wrong (perhaps
    intentionally). The timeout is specified in minutes; and expiration
    date returned is rounded to one second.
    """
    def __init__(self, secret = None, timeout = None, maxlen = None):
        self.timeout = timeout or 30
        self.maxlen  = maxlen or 4096
        self.secret  = secret or sha.sha(str(random.random()) +
                                         str(time.time())).digest()

    def sign(self, content):
        """ 
        Sign the content returning a valid cookie (that does not
        need to be escaped and quoted).  The expiration of this
        cookie is handled server-side in the auth() function.
        """
        cookie = base64.b64encode(
            hmac.new(self.secret,content,sha).digest() +
            make_time(time.time()+60*self.timeout) +
            content).replace("/","_").replace("=","~")
        if len(cookie) > self.maxlen:
            raise CookieTooLarge(content,cookie)
        return cookie

    def auth(self,cookie):
        """ 
        Authenticate the cooke using the signature, verify that it
        has not expired; and return the cookie's content
        """
        decode = base64.b64decode(
            cookie.replace("_","/").replace("~","="))
        signature = decode[:_signature_size]
        expires = decode[_signature_size:_header_size]
        content = decode[_header_size:]
        if signature == hmac.new(self.secret,content,sha).digest():
            if int(expires) > int(make_time(time.time())):
                return content
            else:
                # This is the normal case of an expired cookie; just
                # don't bother doing anything here.
                pass
        else:
            # This case can happen if the server is restarted with a 
            # different secret; or if the user's IP address changed
            # due to a proxy.  However, it could also be a break-in
            # attempt -- so should it be reported?
            pass

class AuthCookieEnviron(list):
    """
    This object is a list of `environ` keys that were restored from or
    will be added to the digially signed cookie.  This object can be
    accessed from an `environ` variable by using this module's name.

      environ['paste.auth.cookie'].append('your.environ.variable')

    This environment-specific object can also be used to access/configure
    the base handler for all requests by using:

      environ['paste.auth.cookie'].handler

    """
    def __init__(self, handler, scanlist):
        list.__init__(self, scanlist)
        self.handler = handler
    def append(self, value):
        if value in self:
            return
        list.append(self,str(value))

class AuthCookieHandler:
    """
    This middleware uses cookies to stash-away a previously authenticated 
    user (and perhaps other variables) so that re-authentication is not
    needed.  This does not implement sessions; and therefore N servers
    can be syncronized to accept the same saved authentication if they
    all use the same cookie_name and secret.

    By default, this handler scans the `environ` for the REMOTE_USER
    key; if found, it is stored. It can be configured to scan other
    `environ` keys as well -- but be careful not to exceed 2-3k (so that
    the encoded and signed cookie does not exceed 4k). You can ask it
    to handle other environment variables by doing:
    
       environ['paste.auth.cookie'].append('your.environ.variable')

    """
    environ_name = 'paste.auth.cookie'
    signer_class = CookieSigner 
    environ_class = AuthCookieEnviron

    def __init__(self, application, cookie_name=None, secret=None, 
                 timeout=None, maxlen=None, signer=None, scanlist = None):
        if not signer:
            signer = self.signer_class(secret,timeout,maxlen)
        self.signer = signer
        self.scanlist = scanlist or ('REMOTE_USER',)
        self.application = application
        self.cookie_name = cookie_name or 'PASTE_AUTH_COOKIE'
    
    def __call__(self, environ, start_response):
        if self.environ_name in environ:
            raise AssertionError("AuthCookie already installed!")
        scanlist = self.environ_class(self,self.scanlist)
        jar = get_cookies(environ)
        if jar.has_key(self.cookie_name):
            content = self.signer.auth(jar[self.cookie_name].value)
            if content:
                for pair in content.split(";"):
                    (k,v) = pair.split("=")
                    k = decode(k)
                    if k not in scanlist:
                        scanlist.append(k)
                    if k in environ:
                        continue
                    environ[k] = decode(v)
                    if 'REMOTE_USER' == k:
                        environ['AUTH_TYPE'] = 'cookie'
        environ[self.environ_name] = scanlist
        if "paste.httpexceptions" in environ:
            warnings.warn("Since paste.httpexceptions is hooked in your "
                "processing chain before paste.auth.cookie, if an "
                "HTTPRedirection is raised, the cookies this module sets "
                "will not be included in your response.\n")

        def response_hook(status, response_headers, exc_info=None):
            """
            Scan the environment for keys specified in the scanlist, 
            pack up their values, signs the content and issues a cookie.
            """
            scanlist = environ.get(self.environ_name)
            assert scanlist and isinstance(scanlist,self.environ_class)
            content = []
            for k in scanlist:
                v = environ.get(k,None)
                if v is not None:
                    content.append("%s=%s" % (encode(k),encode(v)))
            if content:
                content = ";".join(content)
                content = self.signer.sign(content)
                cookie = '%s=%s; Path=/;' % (self.cookie_name, content)
                if 'https' == environ['wsgi.url_scheme']:
                    cookie += ' secure;'
                response_headers.append(('Set-Cookie',cookie))
            return start_response(status, response_headers, exc_info)
        return self.application(environ, response_hook)

middleware = AuthCookieHandler

__all__ = ['AuthCookieHandler']

if '__main__' == __name__:
    from paste.wsgilib import parse_querystring
    def AuthStupidHandler(application):
        def authstupid_application(environ, start_response):
            args = dict(parse_querystring(environ))
            user = args.get('user','')
            if user:
                environ['REMOTE_USER'] = user
                environ['AUTH_TYPE'] = 'stupid'
            test = args.get('test','')
            if test:
                environ['paste.auth.cookie.test'] = test
                environ['paste.auth.cookie'].append('paste.auth.cookie.test')
            return application(environ, start_response)
        return authstupid_application
    from paste.wsgilib import dump_environ
    from paste.util.httpserver import serve
    from paste.httpexceptions import *
    serve(AuthCookieHandler(
            HTTPExceptionHandler(
                  AuthStupidHandler(dump_environ))))
