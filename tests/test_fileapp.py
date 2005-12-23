# (c) 2005 Ian Bicking, Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
from paste.fileapp import *
from paste.fixture import *

def test_data():
    harness = TestApp(DataApp('mycontent'))
    res = harness.get("/")
    assert 'application/octet-stream' == res.header('content-type')
    assert '9' == res.header('content-length')
    assert "<Response 200 OK 'mycontent'>" == repr(res)
    harness.app.set_content("bingles")
    assert "<Response 200 OK 'bingles'>" == repr(harness.get("/"))

def test_cache():
    app = DataApp('mycontent')
    app.cache()
    harness = TestApp(app)
    res = harness.get("/")

def test_modified():
    harness = TestApp(DataApp('mycontent'))
    res = harness.get("/")
    assert "<Response 200 OK 'mycontent'>" == repr(res)
    res = harness.get("/",headers={'if-modified-since':
                                    res.header('last-modified')})
    assert "<Response 304 Not Modified ''>" == repr(res)
    res = harness.get("/",status=400,
            headers={'if-modified-since': 'garbage'})
    assert 400 == res.status and "Bad Timestamp" in res.body
    res = harness.get("/",status=400,
            headers={'if-modified-since':
                'Thu, 22 Dec 2030 01:01:01 GMT'})
    assert 400 == res.status and "Clock Time In Future" in res.body
