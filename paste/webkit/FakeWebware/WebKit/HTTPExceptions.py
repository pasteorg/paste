from paste.httpexceptions import *

class HTTPAuthenticationRequired(HTTPUnauthorized):

    def __init__(self, realm=None, message=None, headers=None):
        headers = headers or {}
        headers['WWW-Authenticate'] = 'Basic realm=%s' % realm
        HTTPUnathorized.__init__(self, message, headers)
