from wsgikit import wsgilib
from wsgikit import login
from fixture import *

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
    return app
    
def test_basicauth_noauth():
    res = fake_request(mk_basic_auth_app(), '/')
    assert res.status_int == 401
    report(res)

def run_userpass(user, password):
    userpass = user + ':' + password
    env = {'HTTP_AUTHORIZATION' : 'Basic ' + userpass.encode('base64')}
    return fake_request(mk_basic_auth_app(), '/', **env)

def test_basicauth_okuser():
    res = run_userpass('test', 'test') # should succeed
    assert res.status_int == 200
    report(res)

def test_basicauth_baduser():
    res = run_userpass('test', 'badpass') # should succeed
    assert res.status_int == 401
    report(res)

def test_basicauth_cookie():
    res = run_userpass('test', 'test') # should succeed
    assert res.status_int == 200
    report(res)
    cookie_val = res.header('SET-COOKIE')
    print "cookie value", cookie_val
    app = mk_basic_auth_app()
    env = {'HTTP_COOKIE': cookie_val}
    res = fake_request(mk_basic_auth_app(), '/', **env)
    report(res)
    assert res.status_int == 200
    
    # ensure that secret is actually used
    res = fake_request(mk_basic_auth_app(secret='bogus'),
                       '/', **env)
    report(res)
    assert res.status_int == 401

if __name__ == '__main__':
    from_cmdline = 1
    test_basicauth_noauth()
    test_basicauth_okuser()
    test_basicauth_baduser()
    test_basicauth_cookie()
    

