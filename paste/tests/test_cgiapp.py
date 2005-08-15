import os
import py.test
from paste.cgiapp import CGIApplication, CGIError
from fixture import *
del setup_module

data_dir = os.path.join(os.path.dirname(__file__), 'cgiapp_data')


def test_ok():
    app = TestApp(CGIApplication('ok.cgi', [data_dir]))
    res = app.get('')
    assert res.header('content-type') == 'text/html; charset=UTF-8'
    assert res.full_status == '200 Okay'
    assert 'This is the body' in res
    
def test_form():
    app = TestApp(CGIApplication('form.cgi', [data_dir]))
    res = app.post('', params={'name': 'joe'},
                   upload_files=[('up', 'file.txt', 'x'*10000)])
    assert 'file.txt' in res
    assert 'joe' in res
    assert 'x'*10000 in res

def test_error():
    app = TestApp(CGIApplication('error.cgi', [data_dir]))
    py.test.raises(CGIError, "app.get('', status=500)")
    
def test_stderr():
    app = TestApp(CGIApplication('stderr.cgi', [data_dir]))
    res = app.get('', expect_errors=True)
    assert res.status == 500
    assert 'error' in res
    assert 'some data' in res.errors
    
