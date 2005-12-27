from paste.httpheaders import *

def _test_generic(collection):
    assert 'bing' == Via(collection)
    Referer.update(collection,'internal:/some/path')
    assert 'internal:/some/path' == Referer(collection)
    ContentDisposition.update(collection,public=None,max_age=1234)
    Pragma.update(collection,"test","multi",'valued="items"')
    #@@: fix ordering issue here, public should be first
    assert 'max-age=1234, public' == ContentDisposition(collection)
    assert 'test, multi, valued="items"' == Pragma(collection)
    Via.delete(collection)


def test_environ():
    collection = {'HTTP_VIA':'bing', 'wsgi.version': '1.0' }
    _test_generic(collection)
    assert collection == {'wsgi.version': '1.0',
      'HTTP_PRAGMA': 'test, multi, valued="items"',
      'HTTP_CONTENT_DISPOSITION': 'max-age=1234, public',
      'HTTP_REFERER': 'internal:/some/path'
    }

def test_response_headers():
    collection = [('via', 'bing')]
    _test_generic(collection)
    normalize_headers(collection)
    assert collection == [
      ('Pragma', 'test, multi, valued="items"'),
      ('Referer', 'internal:/some/path'),
      ('Content-Disposition', 'max-age=1234, public')
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

