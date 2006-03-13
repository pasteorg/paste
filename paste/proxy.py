"""
An application that proxies WSGI requests to a remote server.

TODO:

* Send ``Via`` header?  It's not clear to me this is a Via in the
  style of a typical proxy.

* Other headers or metadata?  I put in X-Forwarded-For, but that's it.

* Signed data of non-HTTP keys?  This would be for things like
  REMOTE_USER.

* Something to indicate what the original URL was?  The original host,
  scheme, and base path.

* Rewriting ``Location`` headers?  mod_proxy does this.

* Rewriting body?  (Probably not on this one -- that can be done with
  a different middleware that wraps this middleware)
"""

import httplib
import urlparse

class Proxy(object):

    def __init__(self, address):
        self.address = address
        self.parsed = urlparse.urlsplit(address)
        self.scheme = self.parsed[0].lower()
        self.host = self.parsed[1]

    def __call__(self, environ, start_response):
        if self.scheme == 'http':
            ConnClass = httplib.HTTPConnection
        elif self.scheme == 'https':
            ConnClass = httplib.HTTPSConnection
        else:
            raise ValueError(
                "Unknown scheme for %r: %r" % (self.address, self.scheme))
        conn = ConnClass(self.host)
        headers = {}
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                key = key[5:].lower().replace('_', '-')
                if key == 'host':
                    continue
                headers[key] = value
        headers['host'] = self.host
        if 'REMOTE_ADDR' in environ:
            headers['x-forwarded-for'] = environ['REMOTE_ADDR']
        if environ.get('CONTENT_TYPE'):
            headers['content-type'] = environ['CONTENT_TYPE']
        if environ.get('CONTENT_LENGTH'):
            length = int(environ['CONTENT_LENGTH'])
            body = environ['wsgi.input'].read(length)
        else:
            body = ''
        print (environ['REQUEST_METHOD'],
                     environ['PATH_INFO'],
                     body, headers)
        conn.request(environ['REQUEST_METHOD'],
                     environ['PATH_INFO'],
                     body, headers)
        res = conn.getresponse()
        # @@: 2.4ism:
        headers_out = res.getheaders()
        status = '%s %s' % (res.status, res.reason)
        start_response(status, headers_out)
        # @@: Default?
        length = res.getheader('content-length')
        body = res.read(int(length))
        conn.close()
        return [body]

def make_proxy(global_conf, address):
    """
    Make a WSGI application that proxies to another address --
    'address' should be the full URL.
    """
    return Proxy(address)
