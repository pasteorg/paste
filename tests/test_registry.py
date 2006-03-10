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

class RegistryUsingIteratorApp(object):
    def __init__(self, var, value):
        self.var = var
        self.value = value
    
    def __call__(self, environ, start_response):
        if environ.has_key('paste.registry'):
            environ['paste.registry'].register(self.var, self.value)
        status = '200 OK'
        response_headers = [('Content-type','text/plain')]
        start_response(status, response_headers)
        return iter(['Hello world!\nThe variable is %s' % str(testobj)])

class RegistryMiddleMan(object):
    def __init__(self, app, var, value, depth):
        self.app = app
        self.var = var
        self.value = value
        self.depth = depth
    
    def __call__(self, environ, start_response):
        if environ.has_key('paste.registry'):
            environ['paste.registry'].register(self.var, self.value)
        app_response = ['\nInserted by middleware!\nInsertValue at depth \
            %s is %s' % (self.depth, str(testobj))]
        app_iter = None
        app_iter = self.app(environ, start_response)
        if type(app_iter) in (list, tuple):
            app_response.extend(app_iter)
        else:
            response = []
            for line in app_iter:
                response.append(line)
            app_iter.close()
            app_response.extend(response)
        app_response.extend(['\nAppended by middleware!\nAppendValue at \
            depth %s is %s' % (self.depth, str(testobj))])
        return app_response
            

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
    
def test_double_registry():
    obj = {'hi':'people'}
    secondobj = {'bye':'friends'}
    wsgiapp = RegistryUsingApp(testobj, obj)
    wsgiapp = RegistryManager(wsgiapp)
    wsgiapp = RegistryMiddleMan(wsgiapp, testobj, secondobj, 0)
    wsgiapp = RegistryManager(wsgiapp)
    app = TestApp(wsgiapp)
    res = app.get('/')
    assert 'Hello world' in res
    assert 'The variable is' in res
    assert "{'hi': 'people'}" in res
    assert "InsertValue at depth 0 is {'bye': 'friends'}" in res
    assert "AppendValue at depth 0 is {'bye': 'friends'}" in res

def test_really_deep_registry():
    keylist = ['fred', 'wilma', 'barney', 'homer', 'marge', 'bart', 'lisa',
        'maggie']
    valuelist = range(0, len(keylist))
    obj = {'hi':'people'}
    wsgiapp = RegistryUsingApp(testobj, obj)
    wsgiapp = RegistryManager(wsgiapp)
    for depth in valuelist:
        newobj = {keylist[depth]: depth}
        wsgiapp = RegistryMiddleMan(wsgiapp, testobj, newobj, depth)
        wsgiapp = RegistryManager(wsgiapp)
    app = TestApp(wsgiapp)
    res = app.get('/')
    assert 'Hello world' in res
    assert 'The variable is' in res
    assert "{'hi': 'people'}" in res
    for depth in valuelist:
        assert "InsertValue at depth %s is {'%s': %s}" % \
            (depth, keylist[depth], depth) in res
    for depth in valuelist:
        assert "AppendValue at depth %s is {'%s': %s}" % \
            (depth, keylist[depth], depth) in res
    
def test_iterating_response():
    obj = {'hi':'people'}
    secondobj = {'bye':'friends'}
    wsgiapp = RegistryUsingIteratorApp(testobj, obj)
    wsgiapp = RegistryManager(wsgiapp)
    wsgiapp = RegistryMiddleMan(wsgiapp, testobj, secondobj, 0)
    wsgiapp = RegistryManager(wsgiapp)
    app = TestApp(wsgiapp)
    res = app.get('/')
    assert 'Hello world' in res
    assert 'The variable is' in res
    assert "{'hi': 'people'}" in res
    assert "InsertValue at depth 0 is {'bye': 'friends'}" in res
    assert "AppendValue at depth 0 is {'bye': 'friends'}" in res
