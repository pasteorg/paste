from paste.httpheaders import *

def test_environ():
    environ = {'HTTP_VIA':'bing', 'wsgi.version': '1.0' }
    assert 'bing' == Via(environ)

def test_response_headers():
    response_headers = [('via', 'bing')]
    assert 'bing' == Via(response_headers)

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

