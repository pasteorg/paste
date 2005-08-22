from paste import wsgilib
from paste import login
from paste.fixture import *

from_cmdline = 0

def application(environ, start_response):
    if environ.has_key('REMOTE_USER'):
	start_response('200 OK', [('Content-type', 'text/plain')])
	return ['Logged in: ' + environ['REMOTE_USER']]
    else:
	start_response('401 Unauthorized',
                       [('Content-type', 'text/plain')])
	return ['Not logged in.']

class AuthTest(login.Authenticator):
    def check_auth(self, username, password):
        return username == password

def report(res):
    if from_cmdline:
        print res
        
# @@ this should be part of a test fixture, I think
def mk_basic_auth_app(**kw):
    kw['http_login'] = True
    kw['authenticator'] =  AuthTest
    app = login.middleware(application, **kw)
    testapp = TestApp(app)
    return testapp
    
def test_basicauth_noauth():
    res = mk_basic_auth_app().get('/', status=401)
    report(res)

def run_userpass(user, password, status=200):
    userpass = user + ':' + password
    env = {'AUTHORIZATION' : 'Basic ' + userpass.encode('base64')}
    return mk_basic_auth_app().get('/', headers=env, status=status)

def test_basicauth_okuser():
    res = run_userpass('test', 'test') # should succeed
    report(res)

def test_basicauth_baduser():
    res = run_userpass('test', 'badpass',
                       status=401) # should succeed
    report(res)

def test_basicauth_cookie():
    res = run_userpass('test', 'test') # should succeed
    report(res)
    cookie_val = res.header('SET-COOKIE')
    print "cookie value", cookie_val
    app = mk_basic_auth_app()
    env = {'Cookie': cookie_val}
    res = app.get('/', headers=env)
    report(res)
    
    # ensure that secret is actually used
    res = mk_basic_auth_app(secret='bogus').get(
        '/', headers=env, status=401, expect_errors=True)
    report(res)

if __name__ == '__main__':
    from_cmdline = 1
    test_basicauth_noauth()
    test_basicauth_okuser()
    test_basicauth_baduser()
    test_basicauth_cookie()
    

