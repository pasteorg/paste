"""
WSGI middleware

Gzip-encodes the response.
"""

import gzip
from cStringIO import StringIO
import wsgilib

class GzipOutput(object):
    pass

class middleware(object):

    def __init__(self, application, compress_level=5):
        self.application = application
        self.compress_level = compress_level

    def __call__(self, environ, start_response):
        if 'gzip' not in environ.get('HTTP_ACCEPT_ENCODING'):
            # nothing for us to do, so this middleware will
            # be a no-op:
            return self.application(environ, start_response)
        response = GzipResponse(start_response, self.compress_level)
        app_iter = self.application(environ,
                                    response.gzip_start_response)
        try:
            if app_iter:
                response.finish_response(app_iter)
        finally:
            response.close()
        return None

class GzipResponse(object):

    def __init__(self, start_response, compress_level):
        self.start_response = start_response
        self.compress_level = compress_level
        self.gzip_fileobj = None

    def gzip_start_response(self, status, headers, exc_info=None):
        # This isn't part of the spec yet:
        if wsgilib.has_header(headers, 'content-encoding'):
            # we won't double-encode
            return self.start_response(status, headers, exc_info)

        headers.append(('content-encoding', 'gzip'))
        raw_writer = self.start_response(status, headers, exc_info)
        dummy_fileobj = GzipOutput()
        dummy_fileobj.write = raw_writer
        self.gzip_fileobj = gzip.GzipFile('', 'wb', self.compress_level,
                                          dummy_fileobj)
        return self.gzip_fileobj.write

    def finish_response(self, app_iter):
        try:
            for s in app_iter:
                self.gzip_fileobj.write(s)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()

    def close(self):
        self.gzip_fileobj.close()
