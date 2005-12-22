"""
Static file sending application
"""
import os, time
import mimetypes
import httpexceptions
from response import has_header, remove_header
from rfc822 import formatdate

CACHE_SIZE = 4096
BLOCK_SIZE = 4096

class DataApp(object):
    """
    Returns an application that will send the data provided.

    Constructor Arguments:

        ``content``     the content being sent to the client

        ``headers``     set of static headers to send /w response
                        - may contain ``content-type`` override
                        - must not contain ``content-length``

        ``mimetype``    if set, this is the mimetype of the content

        ``expires``     if this is set, is the number of seconds
                        from the time of the request that the file
                        is marked to expire

    """
    def __init__(self, content, headers=None, expires=None, mimetype=None):
        self.content = None
        self.headers = headers or []
        self.expires = expires
        if not has_header(self.headers,'content-type'):
            if not mimetype:
                mimetype = 'application/octet-stream'
            self.headers.append(('content-type', mimetype))
        if content:
            self.set_content(content)

    def set_content(self, content):
        self.content = [content]
        remove_header(self.headers,'content-length')
        self.headers.append(('content-length',str(len(content))))

    def __call__(self, environ, start_response):
        headers = self.headers
        if self.expires:
             headers = headers[:]  # copy this array so we can add
             headers.append(('Expires',formatdate(time.time()+self.expires)))
        start_response('200 OK',headers)
        return self.content

class FileApp(DataApp):
    """
    Returns an application that will send the file at the given
    filename.  Adds a mime type based on ``mimetypes.guess_type()``.
    """
    # @@: Should test things like last-modified, if-modified-since,
    # etc.

    def __init__(self, filename, **kwargs):
        self.filename = filename
        self.st_mtime = 0
        if 'mimetype' not in kwargs:
            mimetype, encoding = mimetypes.guess_type(self.filename)
            # @@: I don't know what to do with the encoding.
            if not mimetype:
                mimetype = 'application/octet-stream'
            kwargs['mimetype'] = mimetype
        DataApp.__init__(self, None, **kwargs)

    def update(self):
        stat = os.stat(self.filename)
        if stat.st_mtime == self.st_mtime:
            return
        self.st_mtime = stat.st_mtime
        if  stat.st_size < CACHE_SIZE:
            fh = open(self.filename,"rb")
            self.set_content(fh.read())
            fh.close()
            return
        self.content = None
        remote_header(self.headers,'content-length')
        self.headers.append(('content-length',stat.st_size))

    def __call__(self, environ, start_response):
        self.update()
        if self.content:
            return DataApp.__call__(self, environ, start_response)
        try:
            file = open(self.filename, 'rb')
        except (IOError, OSError), e:
            exc = httpexceptions.HTTPForbidden(
                'You are not permitted to view this file (%s)' % e)
            return exc.wsgi_application(
                environ, start_response)
        DataApp.__call__(self, environ, start_response)
        return _FileIter(file)

class _FileIter:

    def __init__(self, fp, blocksize=BLOCK_SIZE):
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
