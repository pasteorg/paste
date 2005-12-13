# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
Basic Authentication

"""
from paste.httpexceptions import HTTPUnauthorized
   
class BasicAuthenticator:
    """ Implementation of only 'Basic' authentication in 2617 """
    def __init__(self, realm, userfunc):
        """ 
           realm is a globally unique URI like tag:clarkevans.com,2005:basic
                 that represents the authenticating authority
           userfunc(username, password) -> boolean
        """
        self.realm = realm
        self.userfunc = userfunc

    def build_authentication(self):
        head = [('WWW-Authenticate','Basic realm="%s"' % self.realm)]
        return HTTPUnauthorized(headers=head)

    def authenticate(self, authorization):
        if not authorization:
            return self.build_authentication()
        (authmeth, auth) = authorization.split(" ",1)
        if 'basic' != authmeth.lower():
            return self.build_authentication()
        auth = auth.strip().decode('base64')
        username, password = auth.split(':')
        if self.userfunc(username, password):
            return username
        return self.build_authentication()

    __call__ = authenticate

def AuthBasicHandler(application, realm, userfunc):
    authenticator = BasicAuthenticator(realm, userfunc)
    def basic_application(environ, start_response):
        username = environ.get('REMOTE_USER','')
        if not username:
            authorization = environ.get('HTTP_AUTHORIZATION','')
            result = authenticator(authorization)
            if isinstance(result,str):
                environ['AUTH_TYPE'] = 'basic'
                environ['REMOTE_USER'] = result
            else:
                return result.wsgi_application(environ, start_response)
        return application(environ, start_response)
    return basic_application

middleware = AuthBasicHandler

__all__ = ['AuthBasicHandler']

if '__main__' == __name__:
    realm = 'tag:clarkevans.com,2005:basic'
    def userfunc(username, password):
        return username == password
    from paste.wsgilib import dump_environ
    from paste.util.baseserver import serve
    from paste.httpexceptions import *
    serve(HTTPExceptionHandler(
              AuthBasicHandler(dump_environ, realm, userfunc)))
