from paste.httpheaders import *
import time

def _test_generic(collection):
    assert 'bing' == Via(collection)
    Referer.update(collection,'internal:/some/path')
    assert 'internal:/some/path' == Referer(collection)
    CacheControl.update(collection,max_age=1234)
    ContentDisposition.update(collection,filename="bingles.txt")
    Pragma.update(collection,"test","multi",'valued="items"')
    assert 'public, max-age=1234' == CacheControl(collection)
    assert 'attachment, filename="bingles.txt"' == \
            ContentDisposition(collection)
    assert 'test, multi, valued="items"' == Pragma(collection)
    Via.delete(collection)


def test_environ():
    collection = {'HTTP_VIA':'bing', 'wsgi.version': '1.0' }
    _test_generic(collection)
    assert collection == {'wsgi.version': '1.0',
      'HTTP_PRAGMA': 'test, multi, valued="items"',
      'HTTP_REFERER': 'internal:/some/path',
      'HTTP_CONTENT_DISPOSITION': 'attachment, filename="bingles.txt"',
      'HTTP_CACHE_CONTROL': 'public, max-age=1234'
    }

def test_response_headers():
    collection = [('via', 'bing')]
    _test_generic(collection)
    normalize_headers(collection)
    assert collection == [
        ('Cache-Control', 'public, max-age=1234'),
        ('Pragma', 'test, multi, valued="items"'),
        ('Referer', 'internal:/some/path'),
        ('Content-Disposition', 'attachment, filename="bingles.txt"')
    ]

def test_cache_control():
    assert 'public' == CacheControl()
    assert 'public' == CacheControl(public=True)
    assert 'private' == CacheControl(private=True)
    assert 'no-cache' == CacheControl(no_cache=True)
    assert 'private, no-store' == CacheControl(private=True, no_store=True)
    assert 'public, max-age=60' == CacheControl(max_age=60)
    assert 'public, max-age=86400' == \
            CacheControl(max_age=CacheControl.ONE_DAY)
    CacheControl.extensions['community'] = str
    assert 'public, community="bingles"' == \
            CacheControl(community="bingles")
    headers = []
    CacheControl.apply(headers,max_age=60)
    assert 'public, max-age=60' == CacheControl(headers)
    assert Expires.time(headers) > time.time()
    assert Expires.time(headers) < time.time() + 60

def test_content_disposition():
    assert 'attachment' == ContentDisposition()
    assert 'attachment' == ContentDisposition(attachment=True)
    assert 'inline' == ContentDisposition(inline=True)
    assert 'inline, filename="test.txt"' == \
            ContentDisposition(inline=True, filename="test.txt")
    assert 'attachment, filename="test.txt"' == \
            ContentDisposition(filename="/some/path/test.txt")
    headers = []
    ContentDisposition.apply(headers,filename="test.txt")
    assert 'text/plain' == ContentType(headers)
    ContentDisposition.apply(headers,filename="test")
    assert 'text/plain' == ContentType(headers)
    ContentDisposition.apply(headers,filename="test.html")
    assert 'text/plain' == ContentType(headers)
    headers = [('Content-Type', 'application/octet-stream')]
    ContentDisposition.apply(headers,filename="test.txt")
    assert 'text/plain' == ContentType(headers)
    assert headers == [
      ('Content-Type', 'text/plain'),
      ('Content-Disposition', 'attachment, filename="test.txt"')
    ]

def test_copy():
    environ = {'HTTP_VIA':'bing', 'wsgi.version': '1.0' }
    response_headers = []
    Via.update(response_headers,environ)
    assert response_headers == [('Via', 'bing')]

def test_sorting():
    # verify the HTTP_HEADERS are set with their canonical form
    sample = [WWWAuthenticate, Via, Accept, Date,
    AcceptCharset, Age, Allow, CacheControl,
    ContentEncoding, ETag, ContentType, From,
    Expires, Range, Upgrade, Vary, Allow]
    sample.sort()
    sample = [str(x) for x in sample]
    assert sample == [
     # general headers first
     'Cache-Control', 'Date', 'Upgrade', 'Via',
     # request headers next
     'Accept', 'Accept-Charset', 'From', 'Range',
     # response headers following
     'Age', 'ETag', 'Vary', 'WWW-Authenticate',
     # entity headers (/w expected duplicate)
     'Allow', 'Allow', 'Content-Encoding', 'Content-Type', 'Expires'
    ]

def test_normalize():
    response_headers = [
       ('www-authenticate','Response AuthMessage'),
       ('unknown-header','Unknown Sorted Last'),
       ('Via','General Bingles'),
       ('aLLoW','Entity Allow Something'),
       ('ETAG','Response 34234'),
       ('expires','Entity An-Expiration-Date'),
       ('date','General A-Date')]
    normalize_headers(response_headers, strict=False)
    assert response_headers == [
     ('Date', 'General A-Date'),
     ('Via', 'General Bingles'),
     ('ETag', 'Response 34234'),
     ('WWW-Authenticate', 'Response AuthMessage'),
     ('Allow', 'Entity Allow Something'),
     ('Expires', 'Entity An-Expiration-Date'),
     ('Unknown-Header', 'Unknown Sorted Last')]

