from paste.twisted_wsgi import serve_application
from paste import echo, login

def twisted_serve(app):
    serve_application(
        app, port=8080)

class AuthTest(login.Authenticator):
    def check_auth (self, username, password):
        print "checking", username, password
        return username == password

def logincheck (wrapped_app):
    def wrapping_app(environ, start_response):
        k = environ.keys()
        k.sort()
        print "environ", k
        if environ.has_key('REMOTE_USER'):
            return wrapped_app(environ, start_response)
        else:
            start_response('401 Unauthorized',
                           [('Content-type','text/plain')])
            return ['Not logged in.']
    return wrapping_app
            

if __name__ == '__main__':
    app = echo.application
    app = logincheck (app)
    app = login.middleware(
        app, http_login=1, authenticator=AuthTest, secret='foo')
    twisted_serve (app)



