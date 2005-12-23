# (c) 2005 Ian Bicking, Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
from paste.fileapp import *
from paste.fixture import *
from rfc822 import parsedate_tz, mktime_tz
import time

def test_data():
    harness = TestApp(DataApp('mycontent'))
    res = harness.get("/")
    assert 'application/octet-stream' == res.header('content-type')
    assert '9' == res.header('content-length')
    assert "<Response 200 OK 'mycontent'>" == repr(res)
    harness.app.set_content("bingles")
    assert "<Response 200 OK 'bingles'>" == repr(harness.get("/"))

def test_cache():
    def build(*args,**kwargs):
        app = DataApp("SomeContent")
        app.cache(*args,**kwargs)
        return TestApp(app).get("/")
    res = build()
    assert 'public' == res.header('cache-control')
    assert not res.header('expires',None)
    res = build(private=True)
    assert 'private' == res.header('cache-control')
    assert mktime_tz(parsedate_tz(res.header('expires'))) < time.time()
    res = build(no_cache=True)
    assert 'no-cache' == res.header('cache-control')
    assert mktime_tz(parsedate_tz(res.header('expires'))) < time.time()
    res = build(max_age=60,s_maxage=30)
    assert 'public, max-age=60, s-maxage=30' == res.header('cache-control')
    expires = mktime_tz(parsedate_tz(res.header('expires')))
    assert expires > time.time()+58 and expires < time.time()+61
    res = build(private=True, max_age=60, no_transform=True, no_store=True)
    reshead = res.header('cache-control')
    assert 'private, no-store, no-transform, max-age=60' == reshead
    expires = mktime_tz(parsedate_tz(res.header('expires')))
    assert mktime_tz(parsedate_tz(res.header('expires'))) < time.time()

def test_modified():
    harness = TestApp(DataApp('mycontent'))
    res = harness.get("/")
    assert "<Response 200 OK 'mycontent'>" == repr(res)
    res = harness.get("/",headers={'if-modified-since':
                                    res.header('last-modified')})
    assert "<Response 304 Not Modified ''>" == repr(res)
    res = harness.get("/",status=400,
            headers={'if-modified-since': 'garbage'})
    assert 400 == res.status and "ill-formed timestamp" in res.body
    res = harness.get("/",status=400,
            headers={'if-modified-since':
                'Thu, 22 Dec 2030 01:01:01 GMT'})
    assert 400 == res.status and "check your system clock" in res.body

def test_file():
    import random, string, os
    tempfile = "test_fileapp.%s.txt" % (random.random())
    content = string.letters * 20
    file = open(tempfile,"w")
    file.write(content)
    file.close()
    try:
        from paste import fileapp
        app = fileapp.FileApp(tempfile)
        res = TestApp(app).get("/")
        assert len(content) == int(res.header('content-length'))
        assert 'text/plain' == res.header('content-type')
        assert content == res.body
        assert [content] == app.content  # this is cashed
        lastmod = res.header('last-modified')
        print "updating", tempfile
        file = open(tempfile,"a+")
        file.write("0123456789")
        file.close()
        res = TestApp(app).get("/")
        assert len(content)+10 == int(res.header('content-length'))
        assert 'text/plain' == res.header('content-type')
        assert content + "0123456789" == res.body
        assert app.content # we are still cached
        file = open(tempfile,"a+")
        file.write("X" * fileapp.CACHE_SIZE) # exceed the cashe size
        file.close()
        res = TestApp(app).get("/")
        newsize = fileapp.CACHE_SIZE + len(content)+10
        assert newsize == int(res.header('content-length'))
        assert newsize == len(res.body)
        assert res.body.startswith(content) and res.body.endswith('X')
        assert not app.content # we are no longer cached
    finally:
        import os
        os.unlink(tempfile)

