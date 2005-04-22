from wsgikit.urlparser import *
from fixture import fake_request


def path(name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'urlparser_data', name)

def make_parser(name):
    return URLParser(path(name), name, {'index_names': ['index', 'Main']})

def test_find_file():
    p = make_parser('find_file')
    res = fake_request(p, '/')
    assert 'index1' in res
    assert res.header('content-type') == 'text/plain'
    res = fake_request(p, '/index')
    assert 'index1' in res
    assert res.header('content-type') == 'text/plain'
    res = fake_request(p, '/index.txt')
    assert 'index1' in res
    assert res.header('content-type') == 'text/plain'
    res = fake_request(p, '/test2.html')
    assert 'test2' in res
    assert res.header('content-type') == 'text/html'

def test_deep():
    p = make_parser('deep')
    res = fake_request(p, '/')
    assert 'index2' in res
    res = fake_request(p, '/sub')
    assert res.status_int == 301
    print res
    assert res.header('location') == 'http://localhost/sub/'
    assert 'href="http://localhost/sub/"' in res
    res = fake_request(p, '/sub/')
    assert 'index3' in res
    
def test_python():
    p = make_parser('python')
    res = fake_request(p, '/simpleapp')
    res.all_ok()
    assert 'test1' in res
    assert res.header('test-header') == 'TEST!'
    assert res.header('content-type') == 'text/html'
    res = fake_request(p, '/stream')
    res.all_ok()
    assert 'test2' in res
    res = fake_request(p, '/sub/simpleapp')
    res.all_ok()
    assert 'subsimple' in res
    
def test_hook():
    p = make_parser('hook')
    res = fake_request(p, '/bob/app')
    res.all_ok()
    assert 'user: bob' in res
    res = fake_request(p, '/tim/')
    res.all_ok()
    assert 'index: tim' in res
    
def test_not_found_hook():
    p = make_parser('not_found')
    res = fake_request(p, '/simple/notfound')
    assert res.status_int == 200
    assert 'not found' in res
    res = fake_request(p, '/simple/found')
    res.all_ok()
    assert 'is found' in res
    res = fake_request(p, '/recur/__notfound')
    assert res.status_int == 404
    # @@: It's unfortunate that the original path doesn't actually show up
    assert '/recur/notfound' in res
    res = fake_request(p, '/recur/__isfound')
    assert res.status_int == 200
    assert 'is found' in res
    res = fake_request(p, '/user/list')
    res.all_ok()
    assert 'user: None' in res
    res = fake_request(p, '/user/bob/list')
    assert res.status_int == 200
    assert 'user: bob' in res
    
