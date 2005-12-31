# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
Basic HTTP/1.0 Authentication

This module implements ``Basic`` authentication as described in HTTP/1.0
specification [1]_ .  Do not use this module unless you need to work
with very out-dated clients, instead use ``digest`` authentication.
Basically, you just put this module before your application, and it
takes care of requesting and handling authentication requests.

>>> from paste.wsgilib import dump_environ
>>> from paste.util.httpserver import serve
>>> realm = 'Test Realm'
>>> def authfunc(username, password):
...     return username == password
>>> serve(AuthBasicHandler(dump_environ, realm, authfunc))
serving on...

.. [1] http://www.w3.org/Protocols/HTTP/1.0/draft-ietf-http-spec.html#BasicAA
"""
from paste.httpexceptions import HTTPUnauthorized

class AuthBasicAuthenticator:
    """
    implements ``Basic`` authentication details
    """
    type = 'basic'
    def __init__(self, realm, authfunc):
        self.realm = realm
        self.authfunc = authfunc

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
        if self.authfunc(username, password):
            return username
        return self.build_authentication()

    __call__ = authenticate

class AuthBasicHandler:
    """
    HTTP/1.0 ``Basic`` authentication middleware

    Parameters:

        ``application``

            The application object is called only upon successful
            authentication, and can assume ``environ['REMOTE_USER']``
            is set.  If the ``REMOTE_USER`` is already set, this
            middleware is simply pass-through.

        ``realm``

            This is a identifier for the authority that is requesting
            authorization.  It is shown to the user and should be unique
            within the domain it is being used.

        ``authfunc``

            This is a mandatory user-defined function which takes a
            ``username`` and ``password`` for its first and second
            arguments respectively.  It should return ``True`` if
            the user is authenticated.

    """
    def __init__(self, application, realm, authfunc):
        self.application = application
        self.authenticate = AuthBasicAuthenticator(realm, authfunc)

    def __call__(self, environ, start_response):
        username = environ.get('REMOTE_USER','')
        if not username:
            authorization = environ.get('HTTP_AUTHORIZATION','')
            result = self.authenticate(authorization)
            if isinstance(result, str):
                environ['AUTH_TYPE'] = 'basic'
                environ['REMOTE_USER'] = result
            else:
                return result.wsgi_application(environ, start_response)
        return self.application(environ, start_response)

middleware = AuthBasicHandler

__all__ = ['AuthBasicHandler']


if "__main__" == __name__:
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
