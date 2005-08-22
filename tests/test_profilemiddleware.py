from paste.fixture import *
from paste.profilemiddleware import *

def simple_app(environ, start_response):
    start_response('200 OK', [('content-type', 'text/plain')])
    return ['all ok']

def long_func():
    for i in range(1000):
        pass
    return 'test'

def test_profile():
    app = TestApp(ProfileMiddleware(simple_app, {}))
    app.get('/')
    
def test_decorator():
    value = profile_decorator()(long_func)()
    assert value == 'test'
    
