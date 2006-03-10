from paste.fixture import *
from paste.registry import *

testobj = StackedObjectProxy()

def simpleapp(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    return ['Hello world!\n']

class RegistryUsingApp(object):
    def __init__(self, var, value):
        self.var = var
        self.value = value
    
    def __call__(self, environ, start_response):
        if environ.has_key('paste.registry'):
            environ['paste.registry'].register(self.var, self.value)
        status = '200 OK'
        response_headers = [('Content-type','text/plain')]
        start_response(status, response_headers)
        return ['Hello world!\nThe variable is %s' % str(testobj)]

def test_simple():
    app = TestApp(simpleapp)
    response = app.get('/')
    assert 'Hello world' in response

def test_solo_registry():
    obj = {'hi':'people'}
    wsgiapp = RegistryUsingApp(testobj, obj)
    wsgiapp = RegistryManager(wsgiapp)
    app = TestApp(wsgiapp)
    res = app.get('/')
    assert 'Hello world' in res
    assert 'The variable is' in res
    assert "{'hi': 'people'}" in res
    
    