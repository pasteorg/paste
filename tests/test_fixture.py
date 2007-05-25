from paste.debug.debugapp import SimpleApplication
from paste.fixture import TestApp

def test_fixture():
    app = TestApp(SimpleApplication())
    res = app.get('/', params={'a': ['1', '2']})
    assert (res.request.environ['QUERY_STRING'] ==
            'a=1&a=2')
    res = app.put('/')
    assert (res.request.environ['REQUEST_METHOD'] ==
            'PUT')
    res = app.delete('/')
    assert (res.request.environ['REQUEST_METHOD'] ==
            'DELETE')
    
