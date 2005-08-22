"""
Login/authentication middleware

NOT YET FINISHED
"""

import wsgilib
import sha
from paste.deploy import converters
from paste.util import import_string

def middleware(
    application,
    global_conf,
    http_login=False,
    http_realm='Secure Website',
    http_overwrite_realm=True,
    http_and_cookie=True,
    cookie_prefix='',
    login_page='_login/login_form',
    logout_page='_login/logout_form',
    secret=None,
    authenticator=None,
    ):
    """
    Configuration:
    
    http_login:
        If true, then we'll prefer HTTP Basic logins, passing a 401 to
        the user.  If false, we'll use form logins with Cookie
        authentication.
    http_realm:
        The realm to use.  If http_overwrite_realm is true then we will
        force this to be the realm (even if the application supplies
        its own realm).
    http_and_cookie:
        If true, we'll give the user a login cookie even if they use
        HTTP.  Then we don't have to throw a 401 on every page to get
        them to re-login.
    cookie_prefix:
        Used before all cookie names; like a domain.
    login_page:
        If using cookie login and we get a 401, we'll turn it into a
        200 and do an internal redirect to this page (using recursive).
    logout_page:
        Ditto the logout (logout will at some point be triggered with
        another key we add to the environment).
    secret:
        We use this for signing cookies.  We'll generate it automatically
        if it's not provided explicitly (set it explicitly to be sure
        it is stable).
    authenticator:
        When we do HTTP logins we need to tell if they are using the
        correct login immediately.  See the Authenticator object for
        the framework of an implementation.

    When you require a login, return a 401 error.  When a login has
    occurred, the logged-in username will be in REMOTE_USER.  When the
    user is logged in, but denied access, use a 403 error (not a 401).
    It might be useful to have another middleware that wraps an application
    and returns a 401 error, based on parsing the URL.

    Currently, the login form, if used, is rendered at the URL requested
    by the user, instead of issuing an HTTP redirect.  This will require
    some attention to caching issues, but allows forms to be POSTed without
    losing data after the login (as long as the login page contains the
    appropriate hidden fields.)

    Also, the cookie is not deleted on an unsuccessful login attempt.

    The cookie is issued with path '/' and no expiration date.  This
    should probably be overridable.

    Environment variables used:
      paste.login.signer:
          signer, created from UsernameSigner class
      paste.login._dologin:
          user name to be logged in, either from HTTP auth
          or from form submission (XXX form not implement)
      paste.login._doredirect:
          login page to which to redirect
      paste.login._loginredirect:
          set to True iff _doredirect set and login_page is
          relative, else undefined.  Used where?
    """
    
    http_login = converters.asbool(http_login)
    http_overwrite_realm = converters.asbool(http_overwrite_realm)
    http_and_cookie = converters.asbool(http_and_cookie)
    if authenticator and isinstance(authenticator, (str, unicode)):
        authenticator = import_string.eval_import(authenticator)
        
    if http_login:
        assert authenticator, (
            "You must provide an authenticator argument if you "
            "are using http_login")
    if secret is None:
        secret = global_conf.get('secret')
    if secret is None:
        secret = create_secret()
    cookie_name = cookie_prefix + '_login_auth'

    signer = UsernameSigner(secret)

    def login_application(environ, start_response):
        orig_script_name = environ['SCRIPT_NAME']
        orig_path_info = environ['PATH_INFO']
        cookies = wsgilib.get_cookies(environ)
        cookie = cookies.get(cookie_name)
        username = None
        environ['paste.login.signer'] = signer
        if cookie and cookie.value:
            username = signer.check_signature(
                cookie.value, environ['wsgi.errors'])
        authenticatee = (
            environ.get('HTTP_AUTHORIZATION') or
            environ.get('HTTP_CGI_AUTHORIZATION'))
        if (not username
            and authenticator
            and authenticatee):
            username = authenticator().check_basic_auth(authenticatee)
            if http_and_cookie:
                environ['paste.login._dologin'] = username
        if username:
            environ['REMOTE_USER'] = username

        def login_start_response(status, headers, exc_info=None):
            if environ.get('paste.login._dologin'):
                cookie = SimpleCookie(cookie_name,
                                      signer.make_signature(username),
                                      '/')
                headers.append(('Set-Cookie', str(cookie)))
                del environ['paste.login._dologin']
            status_int = int(status.split(None, 1)[0].strip())
            if status_int == 401 and http_login:
                if (http_overwrite_realm
                    or not wsgilib.has_header(headers, 'www-authenticate')):
                    headers.append(('WWW-Authenticate', 'Basic realm="%s"' % http_realm))
            elif status_int == 401:
                status = '200 OK'
                if login_page.startswith('/'):
                    assert environ.has_key('paste.recursive.include'), (
                        "You must use the recursive middleware to "
                        "use a non-relative page for the login_page")
                environ['paste.login._doredirect'] = login_page
                return garbage_writer
            return start_response(status, headers, exc_info)

        app_iter = application(environ, login_start_response)
        
        if environ.get('paste.login._doredirect'):
            page_name = environ['paste.login._doredirect']
            del environ['paste.login._doredirect']
            eat_app_iter(app_iter)
            if login_page.startswith('/'):
                app_iter = environ['paste.recursive.forward'](
                    login_page[1:])
            else:
                # Don't use recursive, since login page is
                # internal to 
                new_environ = environ.copy()
                new_environ['SCRIPT_NAME'] = orig_script_name
                new_environ['PATH_INFO'] = '/' + login_page
                new_environ['paste.login._loginredirect'] = True
                app_iter = login_application(new_environ, start_response)
        return app_iter

    return login_application

    
def encodestrip(s):
    return s.encode('base64').strip('\n')

class UsernameSigner(object):

    def __init__(self, secret):
        self.secret = secret

    def digest(self, username):
        return sha.new(self.secret+username).digest()        

    def __call__(self, username):
        return encodestrip(self.digest(username))

    def check_signature(self, b64value, errors):
        value = b64value.decode('base64')
        if ' ' not in value:
            errors.write('Badly formatted cookie: %r\n' % value)
            return None
        signature, username = value.split(' ', 1)
        sig_hash = self.digest(username)
        if sig_hash == signature:
            return username
        errors.write('Bad signature: %r\n' % value)
        return None
    
    def make_signature(self, username):
        return encodestrip(self.digest(username) + " " + username)

    def login_user(self, username, environ):
        """
        Adds a username so that the login middleware will later set
        the user to be logged in (with a cookie).
        """
        environ['paste.login._dologin'] = username

class SimpleCookie(object):
    def __init__(self, cookie_name, signed_val, path):
        self.cookie_name = cookie_name
        self.signed_val = signed_val
        self.path = '/'

    def __str__(self):
        return "%s=%s; Path=%s" % (self.cookie_name,
                                   self.signed_val, self.path)
    
class Authenticator(object):

    """
    This is the basic framework for an authenticating object.
    """

    def check_basic_auth(self, auth):
        """Returns either the authenticated username or, if unauthorized,
        None."""
        assert auth.lower().startswith('basic ')
        type, auth = auth.split()
        auth = auth.strip().decode('base64')
        username, password = auth.split(':')
        if self.check_auth(username, password):
            return username
        return None

    def check_auth(self, username, password):
        raise NotImplementedError


########################################
## Utility functions
########################################

def create_secret():
    # @@: obviously not a good secret generator: should be randomized
    # somehow, and maybe store the secret somewhere for later use.
    return 'secret'

def garbage_writer(s):
    """
    When we don't care about the written output.
    """
    pass

def eat_app_iter(app_iter):
    """
    When we don't care about the iterated output.
    """
    try:
        for s in app_iter:
            pass
    finally:
        if hasattr(app_iter, 'close'):
            app_iter.close()

    
