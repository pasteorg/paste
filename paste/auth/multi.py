# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
Authentication via Multiple Methods

In some environments, the choice of authentication method to be used
depends upon the environment and is not "fixed".  This middleware allows
N authentication methods to be registered along with a goodness function
which determines which method should be used.

Strictly speaking this is not limited to authentication, but it is a
common requirement in that domain; this is why it isn't named
AuthMultiHandler (for now).
"""

class MultiHandler:
    """
    Multiple Authentication Handler

    This middleware provides two othogonal facilities:

      - a manner to register any number of authentication middlewares

      - a mechanism to register predicates which cause one of the
        registered middlewares to be used depending upon the request

    If none of the predicates returns True, then the application is
    invoked directly without middleware
    """
    def __init__(self, application):
        self.application = application
        self.default = application
        self.binding = {}
        self.predicate = []
    def add_method(self, name, factory, *args, **kwargs):
        self.binding[name] = factory(self.application, *args, **kwargs)
    def add_predicate(self, name, checker):
        self.predicate.append((checker,self.binding[name]))
    def set_default(self, name):
        """ set default authentication method """
        self.default = self.binding[name]
    def set_query_argument(self, name, key = '*authmeth', value = None):
        """ choose authentication method based on a query argument """
        lookfor = "%s=%s" % (key, value or name)
        self.add_predicate(name, 
            lambda environ: lookfor in environ.get('QUERY_STRING',''))
    def __call__(self, environ, start_response):
        for (checker,binding) in self.predicate:
            if checker(environ):
                return binding(environ, start_response)
        return self.default(environ, start_response)

middleware = MultiHandler

__all__ = ['MultiHandler']

if '__main__' == __name__:
    import basic, digest, cas, cookie, form
    from paste.httpexceptions import *
    from paste.wsgilib import dump_environ
    from paste.util.httpserver import serve
    multi = MultiHandler(dump_environ)
    multi.add_method('basic',basic.middleware,
                     'tag:clarkevans.com,2005:basic',
                     lambda n,p: n == p )
    multi.set_query_argument('basic')
    multi.add_method('digest',digest.middleware,
                     'tag:clarkevans.com,2005:digest',
                     lambda r,u: digest.digest_password(u,r,u))
    multi.set_query_argument('digest')
    multi.add_method('form',lambda ap: cookie.middleware(
                                           form.middleware(ap,
                                               lambda n,p: n == p)))
    multi.set_query_argument('form')
    #authority = "https://secure.its.yale.edu/cas/servlet/"
    #multi.add_method('cas',lambda ap: cookie.middleware(
    #                                      cas.middleware(ap,authority)))
    #multi.set_default('cas')
    serve(HTTPExceptionHandler(multi))
