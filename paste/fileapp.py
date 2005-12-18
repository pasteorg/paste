"""
Static file sending application
"""
import os
import mimetypes
import httpexceptions

class FileApp(object):
    """
    Returns an application that will send the file at the given
    filename.  Adds a mime type based on ``mimetypes.guess_type()``.
    """
    # @@: Should test things like last-modified, if-modified-since,
    # etc.

    def __init__(self, filename):
        self.filename = filename

    def __call__(self, environ, start_response):
        type, encoding = mimetypes.guess_type(self.filename)
        # @@: I don't know what to do with the encoding.
        if not type:
            type = 'application/octet-stream'
        size = os.stat(self.filename).st_size
        try:
            file = open(self.filename, 'rb')
        except (IOError, OSError), e:
            exc = httpexceptions.HTTPForbidden(
                'You are not permitted to view this file (%s)' % e)
            return exc.wsgi_application(
                environ, start_response)
        start_response('200 OK',
                       [('content-type', type),
                        ('content-length', str(size))])
        return _FileIter(file)

class _FileIter:

    def __init__(self, fp, blocksize=4096):
        self.file = fp
        self.blocksize = blocksize

    def __iter__(self):
        return self

    def next(self):
        data = self.file.read(self.blocksize)
        if not data:
            raise StopIteration
        return data

    def close(self):
        self.file.close()
