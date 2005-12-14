# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
HTTP Form Authentication

"""
from paste.wsgilib import parse_formvars, construct_url

template = """\
<html>
  <head><title>Please Login</title></head>
  <body>
    <h1>Please Login</h1>
    <form action="%s" method="post">
      <dl>
        <dt>Username:</dt>
        <dd><input type="text" name="username"></dd>
        <dt>Password:</dt>
        <dd><input type="password" name="password"></dd>
      </dl>
      <input type="submit" name="authform" />
      <hr />
    </form>
  </body>
</html>
"""

def AuthFormHandler(application, userfunc, login_page = None):
    """ This causes a HTML form to be returned if REMOTE_USER has not 
        been provided.  This is a really simple implementation, it 
        requires that the query arguments returned from the form have two
        variables "username" and "password".  These are then passed to
        the userfunc; which should return True if authentication is granted.
    """
    login_page = login_page or template
    def form_application(environ, start_response):
        username = environ.get('REMOTE_USER','')
        if username:
            return application(environ, start_response)
        if 'POST' == environ['REQUEST_METHOD']:
            formvars = parse_formvars(environ)
            username = formvars.get('username')
            password = formvars.get('password')
            if username and password:
                if userfunc(username,password):
                    environ['AUTH_TYPE'] = 'form'
                    environ['REMOTE_USER'] = username
                    environ['REQUEST_METHOD'] = 'GET'
                    del environ['paste.parsed_formvars']
                    return application(environ, start_response)
        start_response("200 OK",(('Content-Type', 'text/html'),
                                 ('Content-Length', len(login_page))))
        if "%s" in login_page:
             return [login_page % construct_url(environ) ]
        return [login_page]
    return form_application

middleware = AuthFormHandler

__all__ = ['AuthFormHandler']

if '__main__' == __name__:
    def userfunc(username, password):
        return username == password
    from paste.wsgilib import dump_environ
    from paste.util.httpserver import serve
    from paste.httpexceptions import *
    from cookie import AuthCookieHandler
    serve(HTTPExceptionHandler(
              AuthCookieHandler(
                   AuthFormHandler(dump_environ, userfunc))))
