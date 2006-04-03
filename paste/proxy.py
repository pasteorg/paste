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

* Example::  
    
    use = egg:Paste#proxy
    address = http://server3:8680/exist/rest/db/orgs/sch/config/
    allowed_request_methods = GET
  
"""

import httplib
import urlparse

from paste import httpexceptions

# Remove these headers from response (specify lower case header
# names):
filtered_headers = (     
    'transfer-encoding',    
)

class Proxy(object):

    def __init__(self, address, allowed_request_methods=()):
        self.address = address
        self.parsed = urlparse.urlsplit(address)
        self.scheme = self.parsed[0].lower()
        self.host = self.parsed[1]
        self.path = self.parsed[2]
        self.allowed_request_methods = [
            x.lower() for x in allowed_request_methods if x]
        

    def __call__(self, environ, start_response):
        if (self.allowed_request_methods and 
            environ['REQUEST_METHOD'].lower() not in self.allowed_request_methods):
            return httpexceptions.HTTPBadRequest("Disallowed")(environ, start_response)

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
            
        if self.path:            
            request_path = environ['PATH_INFO']
            if request_path[0] == '/':
                request_path = request_path[1:]
                
            path = urlparse.urljoin(self.path, request_path)
        else:
            path = environ['PATH_INFO']
            
        conn.request(environ['REQUEST_METHOD'],
                     path,
                     body, headers)
        res = conn.getresponse()
        headers_out = []
        for header, value in res.getheaders():
            if header.lower() not in filtered_headers:
                headers_out.append((header, value))
                
        status = '%s %s' % (res.status, res.reason)
        start_response(status, headers_out)
        # @@: Default?
        length = res.getheader('content-length')
        if length is not None:
            body = res.read(int(length))
        else:
            body = res.read()
        conn.close()
        return [body]

def make_proxy(global_conf, address, allowed_request_methods=""):
    """
    Make a WSGI application that proxies to another address --
    'address' should be the full URL ending with a trailing /
    'allowed_request_methods' is a space seperated list of request methods
    """
    from paste.deploy.converters import aslist
    allowed_request_methods = aslist(allowed_request_methods)
    return Proxy(address, allowed_request_methods=allowed_request_methods)
