import cgi

from paste.debug.debugapp import SimpleApplication, SlowConsumer
from paste.fixture import TestApp
from paste.wsgiwrappers import WSGIRequest


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
    class FakeDict(object):
        def items(self):
            return [('a', '10'), ('a', '20')]
    res = app.post('/params', params=FakeDict())

    # test multiple cookies in one request
    app.cookies['one'] = 'first';
    app.cookies['two'] = 'second';
    app.cookies['three'] = '';
    res = app.get('/')
    hc = res.request.environ['HTTP_COOKIE'].split('; ');
    assert ('one=first' in hc)
    assert ('two=second' in hc)
    assert ('three=' in hc)


def test_fixture_form():
    app = TestApp(SlowConsumer())
    res = app.get('/')
    form = res.forms[0]
    assert 'file' in form.fields
    assert form.action == ''


def test_fixture_form_end():
    def response(environ, start_response):
        body = b"<html><body><form>sm\xc3\xb6rebr\xc3\xb6</form></body></html>"
        start_response("200 OK", [('Content-Type', 'text/html'),
                                  ('Content-Length', str(len(body)))])
        return [body]
    TestApp(response).get('/')

def test_params_and_upload_files():
    class PostApp(object):
        def __call__(self, environ, start_response):
            start_response("204 No content", [])
            self.request = WSGIRequest(environ)
            return [b'']
    post_app = PostApp()
    app = TestApp(post_app)
    app.post(
        '/',
        params={'param1': 'a', 'param2': 'b'},
        upload_files=[
            ('file1', 'myfile.txt', b'data1'),
            ('file2', b'yourfile.txt', b'data2'),
        ],
    )
    params = post_app.request.params
    assert len(params) == 4
    assert params['param1'] == 'a'
    assert params['param2'] == 'b'
    assert params['file1'].value == b'data1'
    assert params['file1'].filename == 'myfile.txt'
    assert params['file2'].value == b'data2'
    assert params['file2'].filename == 'yourfile.txt'

def test_unicode_path():
    app = TestApp(SimpleApplication())
    app.get(u"/?")
    app.post(u"/?")
    app.put(u"/?")
    app.delete(u"/?")
