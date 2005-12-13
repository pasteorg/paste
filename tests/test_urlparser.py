import os
from paste.urlparser import *
from paste.fixture import *

def path(name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'urlparser_data', name)

def make_app(name):
    app = URLParser({}, path(name), name, index_names=['index', 'Main'])
    testapp = TestApp(app)
    return testapp

def test_find_file():
    app = make_app('find_file')
    res = app.get('/')
    assert 'index1' in res
    assert res.header('content-type') == 'text/plain'
    res = app.get('/index')
    assert 'index1' in res
    assert res.header('content-type') == 'text/plain'
    res = app.get('/index.txt')
    assert 'index1' in res
    assert res.header('content-type') == 'text/plain'
    res = app.get('/test2.html')
    assert 'test2' in res
    assert res.header('content-type') == 'text/html'

def test_deep():
    app = make_app('deep')
    res = app.get('/')
    assert 'index2' in res
    res = app.get('/sub')
    assert res.status == 301
    print res
    assert res.header('location') == 'http://localhost/sub/'
    assert 'http://localhost/sub/' in res
    res = app.get('/sub/')
    assert 'index3' in res
    
def test_python():
    app = make_app('python')
    res = app.get('/simpleapp')
    assert 'test1' in res
    assert res.header('test-header') == 'TEST!'
    assert res.header('content-type') == 'text/html'
    res = app.get('/stream')
    assert 'test2' in res
    res = app.get('/sub/simpleapp')
    assert 'subsimple' in res
    
def test_hook():
    app = make_app('hook')
    res = app.get('/bob/app')
    assert 'user: bob' in res
    res = app.get('/tim/')
    assert 'index: tim' in res
    
def test_not_found_hook():
    app = make_app('not_found')
    res = app.get('/simple/notfound')
    assert res.status == 200
    assert 'not found' in res
    res = app.get('/simple/found')
    assert 'is found' in res
    res = app.get('/recur/__notfound', status=404)
    # @@: It's unfortunate that the original path doesn't actually show up
    assert '/recur/notfound' in res
    res = app.get('/recur/__isfound')
    assert res.status == 200
    assert 'is found' in res
    res = app.get('/user/list')
    assert 'user: None' in res
    res = app.get('/user/bob/list')
    assert res.status == 200
    assert 'user: bob' in res
    
def test_static_parser():
    app = StaticURLParser(path('find_file'))
    testapp = TestApp(app)
    res = testapp.get('', status=301)
    res = testapp.get('/', status=404)
    res = testapp.get('/index.txt')
    assert res.body.strip() == 'index1'
    res = testapp.get('/index.txt/foo', status=400)
    
def test_egg_parser():
    app = PkgResourcesParser('Paste', 'paste')
    testapp = TestApp(app)
    res = testapp.get('', status=301)
    res = testapp.get('/', status=404)
    res = testapp.get('/flup_session', status=404)
    res = testapp.get('/util/classinit.py')
    assert 'ClassInitMeta' in res
    res = testapp.get('/util/classinit', status=404)
    res = testapp.get('/util', status=301)
    res = testapp.get('/util/classinit.py/foo', status=400)
