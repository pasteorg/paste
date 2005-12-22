# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
HTTP Digest Authentication (RFC 2617)

NOTE: This has not been audited by a security expert, please use
      with caution (or better yet, report security holes).

      At this time, this implementation does not provide for further
      challenges, nor does it support Authentication-Info header.  It
      also uses md5, and an option to use sha would be a good thing.
"""
from paste.httpexceptions import HTTPUnauthorized
import md5, time, random, urllib2

def digest_password(username, realm, password):
    """ Constructs the appropriate hashcode needed for HTTP Digest """
    return md5.md5("%s:%s:%s" % (username,realm,password)).hexdigest()

def response(challenge, realm, path, username, password):
    """
    Build an authorization response for a given challenge.  This
    implementation uses urllib2 to do the dirty work.
    """
    auth = urllib2.AbstractDigestAuthHandler()
    auth.add_password(realm,path,username,password)
    (token,challenge) = challenge.split(' ',1)
    chal = urllib2.parse_keqv_list(urllib2.parse_http_list(challenge))
    class FakeRequest:
       def get_full_url(self):
           return path
       def has_data(self):
           return False
       def get_method(self):
           return "GET"
       get_selector = get_full_url
    return "Digest %s" % auth.get_authorization(FakeRequest(), chal)

class DigestAuthenticator:
    """ Simple implementation of RFC 2617 - HTTP Digest Authentication """
    def __init__(self, realm, userfunc):
        """
            realm is a globally unique URI, like tag:clarkevans.com,2005:bing
            userfunc(realm, username) -> MD5('%s:%s:%s') % (user,realm,pass)
        """
        self.nonce    = {} # list to prevent replay attacks
        self.userfunc = userfunc
        self.realm    = realm

    def build_authentication(self, stale = ''):
        """ raises an authentication exception """
        nonce  = md5.md5("%s:%s" % (time.time(),random.random())).hexdigest()
        opaque = md5.md5("%s:%s" % (time.time(),random.random())).hexdigest()
        self.nonce[nonce] = None
        parts = { 'realm': self.realm, 'qop': 'auth',
                  'nonce': nonce, 'opaque': opaque }
        if stale:
            parts['stale'] = 'true'
        head = ", ".join(['%s="%s"' % (k,v) for (k,v) in parts.items()])
        head = [("WWW-Authenticate", 'Digest %s' % head)]
        return HTTPUnauthorized(headers=head)

    def compute(self, ha1, username, response, method, 
                      path, nonce, nc, cnonce, qop):
        """ computes the authentication, raises error if unsuccessful """
        if not ha1:
            return self.build_authentication()
        ha2 = md5.md5('%s:%s' % (method,path)).hexdigest()
        if qop:
            chk = "%s:%s:%s:%s:%s:%s" % (ha1,nonce,nc,cnonce,qop,ha2)
        else:
            chk = "%s:%s:%s" % (ha1,nonce,ha2)
        if response != md5.md5(chk).hexdigest():
            if nonce in self.nonce:
                del self.nonce[nonce]
            return self.build_authentication()
        pnc = self.nonce.get(nonce,'00000000')
        if nc <= pnc:
            if nonce in self.nonce:
                del self.nonce[nonce]
            return self.build_authentication(stale = True)
        self.nonce[nonce] = nc
        return username

    def authenticate(self, authorization, path, method):
        """ This function takes the value of the 'Authorization' header,
            the method used (e.g. GET), and the path of the request
            relative to the server. The function either returns an
            authenticated user, or it raises an exception.
        """
        if not authorization:
            return self.build_authentication()
        (authmeth, auth) = authorization.split(" ",1)
        if 'digest' != authmeth.lower():
            return self.build_authentication()
        amap = {}
        for itm in auth.split(", "):
            (k,v) = [s.strip() for s in itm.split("=",1)]
            amap[k] = v.replace('"','')
        try:
            username = amap['username']
            authpath = amap['uri']
            nonce    = amap['nonce']
            realm    = amap['realm']
            response = amap['response']
            assert authpath.split("?",1)[0] in path
            assert realm == self.realm
            qop      = amap.get('qop','')
            cnonce   = amap.get('cnonce','')
            nc       = amap.get('nc','00000000')
            if qop:
                assert 'auth' == qop
                assert nonce and nc
        except:
            return self.build_authentication()
        ha1 = self.userfunc(realm,username)
        return self.compute(ha1, username, response, method, authpath,
                            nonce, nc, cnonce, qop)

    __call__ = authenticate

def AuthDigestHandler(application, realm, userfunc):
    """
    This middleware implements HTTP Digest authentication (RFC 2617) on
    the incoming request.  There are several possible outcomes:

    0. If the REMOTE_USER environment variable is already populated;
       then this middleware is a no-op, and the request is passed along
       to the application.

    1. If the HTTP_AUTHORIZATION header was not provided, then a
       HTTPUnauthorized exception is raised containing the challenge.

    2. If the HTTP_AUTHORIZATION header specifies anything other
       than digest; the REMOTE_USER is left unset and application
       processing continues.

    3. If the response is malformed or or if the user's credientials
       do not pass muster, another HTTPUnauthorized is raised.

    4. IF all goes well, and the user's credintials pass; then
       REMOTE_USER environment variable is filled in and the
       AUTH_TYPE is listed as 'digest'.

    Besides the application to delegate requests, this middleware
    requires two additional arguments:

    realm:
        This is a globally unique identifier used to indicate the
        authority that is performing the authentication.  The taguri
        such as tag:yourdomain.com,2006 is sufficient.

    userfunc:
        This is a callback function which performs the actual
        authentication; the signature of this callback is:

          userfunc(realm, username) -> hashcode

        This module provides a 'digest_password' helper function which
        can help construct the hashcode; it is recommended that the
        hashcode is stored in a database, not the user's actual password.
    """
    authenticator = DigestAuthenticator(realm, userfunc)
    def digest_application(environ, start_response):
        username = environ.get('REMOTE_USER','')
        if not username:
            method = environ['REQUEST_METHOD']
            fullpath = environ['SCRIPT_NAME'] + environ["PATH_INFO"]
            authorization = environ.get('HTTP_AUTHORIZATION','')
            result = authenticator(authorization, fullpath, method)
            if isinstance(result, str):
                environ['AUTH_TYPE'] = 'digest'
                environ['REMOTE_USER'] = result
            else:
                return result.wsgi_application(environ, start_response)
        return application(environ, start_response)
    return digest_application

middleware = AuthDigestHandler

__all__ = ['digest_password', 'AuthDigestHandler' ]

if '__main__' == __name__:
    realm = 'tag:clarkevans.com,2005:digest'
    def userfunc(realm, username):
        return digest_password(username, realm, username)
    from paste.wsgilib import dump_environ
    from paste.util.httpserver import serve
    from paste.httpexceptions import *
    serve(HTTPExceptionHandler(
             AuthDigestHandler(dump_environ, realm, userfunc)))
