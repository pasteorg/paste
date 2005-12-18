# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from paste.auth import digest
from paste.wsgilib import raw_interactive
from paste.response import header_value
from paste.httpexceptions import *
import os

def application(environ, start_response):
    content = environ.get('REMOTE_USER','')
    start_response("200 OK",(('Content-Type', 'text/plain'),
                             ('Content-Length', len(content))))
    return content

realm = "tag:clarkevans.com,2005:testing"

def backwords(realm,username):
    """ dummy password hash, where user password is just reverse """
    password = list(username)
    password.reverse()
    password = "".join(password)
    return digest.digest_password(username,realm,password)

application = digest.middleware(application,realm,backwords)
application = HTTPExceptionHandler(application) 

def check(username, password, path="/"):
    """ perform two-stage authentication to verify login """
    (status,headers,content,errors) = \
        raw_interactive(application,path, accept='text/html')
    assert status.startswith("401")
    challenge = header_value(headers,'WWW-Authenticate')
    response = digest.response(challenge, realm, path, username, password)
    assert "Digest" in response
    (status,headers,content,errors) = \
        raw_interactive(application,path,
                        HTTP_AUTHORIZATION=response)
    if status.startswith("200"):
        return content
    if status.startswith("401"):
        return None
    assert False, "Unexpected Status: %s" % status

def test_digest():
    assert 'bing' == check("bing","gnib")
    assert check("bing","bad") is None

#
# The following code uses sockets to test the functionality,
# to enable use:
#
# $ TEST_SOCKET py.test
#

if os.environ.get("TEST_SOCKET",""):
    import urllib2
    from paste.debug.testserver import serve
    server = serve(application)

    def authfetch(username,password,path="/",realm=realm):
        server.accept(2)
        import socket
        socket.setdefaulttimeout(5)
        uri = ("http://%s:%s" % server.server_address) + path
        auth = urllib2.HTTPDigestAuthHandler()
        auth.add_password(realm,uri,username,password)
        opener = urllib2.build_opener(auth)
        result = opener.open(uri)
        return result.read()

    def test_success():
        assert "bing" == authfetch('bing','gnib')

    def test_failure():
        # urllib tries 5 more times before it gives up
        server.accept(5) 
        try:
            authfetch('bing','wrong')
            assert False, "this should raise an exception"
        except urllib2.HTTPError, e:
            assert e.code == 401

    def test_shutdown():
        server.stop()

