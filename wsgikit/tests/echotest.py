"""
Tests a WSGI stack, using urllib.  Queries the echo application.
"""

import unittest
import urlparse
import urllib
import os
import sys

class EchoTest(unittest.TestCase):

    def url(self):
        if not os.environ.get('ECHO_URL'):
            print 'You must set $ECHO_URL'
            sys.exit(1)
        url = URL(os.environ['ECHO_URL'])
        return url

class TestEnviron(EchoTest):

    def setUp(self):
        self.page = self.url().fetch(environ='true')
        self.environ = parse_environ(self.page)

    def testRequiredKeys(self):
        environ = self.environ
        url = self.url()
        required_keys = 'REQUEST_METHOD SCRIPT_NAME PATH_INFO QUERY_STRING SERVER_NAME SERVER_PORT wsgi.errors wsgi.input wsgi.multiprocess wsgi.multithread wsgi.version'
        for key in required_keys.split():
            assert environ.has_key(key), "Key %r missing from %r" % (key, environ)
        self.assertEqual(environ['PATH_INFO'], '')
        self.assertEqual(environ['SCRIPT_NAME'], url.path)
        self.assertEqual(environ['REQUEST_METHOD'], 'GET')
        self.assertEqual(environ['QUERY_STRING'], 'environ=true')
        self.assertEqual(environ['SERVER_PORT'], str(url.port))
        self.assertEqual(environ['SERVER_NAME'], url.host)
        self.assertEqual(environ['HTTP_HOST'], url.location)
        assert environ['HTTP_USER_AGENT'].startswith('Python-urllib/'), \
                         "HTTP_USER_AGENT should start with 'Python-urllib/': %r" % environ['HTTP_USER_AGENT']

    def testPathInfo(self):
        sub = self.url() / ''
        environ = parse_environ(sub.fetch(environ='true'))
        self.assertEqual(environ['PATH_INFO'], '/')
        self.assertEqual(environ['SCRIPT_NAME'], self.url().path)
        sub = self.url() / 'test'
        environ = parse_environ(sub.fetch(environ='true'))
        self.assertEqual(environ['PATH_INFO'], '/test')
        self.assertEqual(environ['SCRIPT_NAME'], self.url().path)

    def test_message(self):
        data = self.url().fetch(message='test')
        self.assertEqual(data, 'test')
        data = self.url().fetch(message='')
        self.assertEqual(data, '')

############################################################
## Utility functions
############################################################

def parse_environ(page):
    """
    Parses the environment that echo prints (not perfect, but good
    enough).
    """
    environ = {}
    for line in page.splitlines():
        if '=' not in line:
            # ignore second line of long lines
            continue
        name, value = line.split('=', 1)
        environ[name] = value
    return environ

class URL:

    def __init__(self, url_string):
        self.url_string = url_string
        (self.scheme, self.location, self.path, self.query,
         self.fragment) = urlparse.urlsplit(url_string)
        if ':' in self.location:
            self.host, self.port = location.split(':', 1)
        else:
            self.host = self.location
            if self.scheme == 'http':
                self.port = '80'
            elif self.scheme == 'https':
                self.port = '443'
            else:
                assert 0, "Unknown scheme: %r" % scheme
        self.port = int(self.port)
        
    def fetch(self, **kw):
        query = '&'.join(['%s=%s' % (urllib.quote(k), urllib.quote(v))
                          for k, v in kw.items()])
        url = self.url_string
        if query:
            url += '?' + query
        f = urllib.urlopen(url)
        page = f.read()
        f.close()
        return page

    def __div__(self, path_part):
        return self.__class__(self.url_string + '/' + path_part)

if __name__ == '__main__':
    unittest.main()
