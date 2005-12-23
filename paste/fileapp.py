# (c) 2005 Ian Bicking, Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""
This module handles sending static content such as in-memory data or
files.  At this time it has cache helpers and understands the
if-modified-since request header.
"""
#@@: this still needs Range support for large files
import os, time
import mimetypes
import httpexceptions
from response import has_header, replace_header
from rfc822 import formatdate, parsedate_tz, mktime_tz
from httpexceptions import HTTPBadRequest

CACHE_SIZE = 4096
BLOCK_SIZE = 4096

__all__ = ['DataApp','FileApp']

class DataApp(object):
    """
    Returns an application that will send content in a single chunk,
    this application has support for setting cashe-control and for
    responding to conditional (or HEAD) requests.

    Constructor Arguments:

        ``content``     the content being sent to the client

        ``headers``     the headers to send /w the response

        The remaining ``kwargs`` correspond to headers, where the
        underscore is replaced with a dash.  These values are only
        added to the headers if they are not already provided; thus,
        they can be used for default values.  Examples include, but
        are not limited to:

            ``content_type``
            ``content_encoding``
            ``content_location``

    ``cache()``

        This method provides validated construction of the ``Cache-Control``
        header as well as providing for automated filling out of the
        ``Expires`` header for HTTP/1.0 clients.

    ``set_content()``

        This method provides a mechanism to set the content after the
        application has been constructed.  This method does things
        like changing ``Last-Modified`` and ``Content-Length`` headers.

    """
    def __init__(self, content, headers=None, **kwargs):
        assert isinstance(headers,(type(None),list))
        self.expires = None
        self.content = None
        self.last_modified = 0
        self.headers = headers or []
        for (k,v) in kwargs.items():
            hk = k.replace("_","-")
            if not headers or not has_header(self.headers,hk):
                self.headers.append((hk,v))
        if not has_header(self.headers,'content-type'):
            self.headers.append(('content-type','application/octet-stream'))
        if content:
            self.set_content(content)

    def cache(self, public=None, private=None, no_cache=None,
              no_store=False, max_age=None, s_maxage=None,
              no_transform=False, **extensions):
        """
        Sets the ``Cache-Control`` according to the arguments provided.
        See RFC 2616 section 14.9 for more details.

          ``public``        if True, this argument specifies that the
                            response, as a whole, may be cashed.

          ``private``       if True, this argument specifies that the
                            response, as a whole, may be cashed; this
                            implementation does not support the
                            enumeration of private fields

          ``no_cache``      if True, this argument specifies that the
                            response, as a whole, may be cashed; this
                            implementation does not support the
                            enumeration of private fields

          In general, only one of the above three may be True, the other
          2 must then be False or None.  If all three are None, then the
          cashe is assumed to be ``public``.  These are distinct fields
          since support for field enumeration may be added in the future.

          ``no_store``      indicates if content may be stored on disk;
                            otherwise cashe is limited to memory (note:
                            users can still save the data, this applies
                            to intermediate caches)

          ``max_age``       the maximum duration (in seconds) for which
                            the content should be cached; if ``no-cache``
                            is specified, this defaults to 0 seconds

          ``s_maxage``      the maximum duration (in seconds) for which the
                            content should be allowed in a shared cache.

          ``no_transform``  specifies that an intermediate cache should
                            not convert the content from one type to
                            another (e.g. transform a BMP to a PNG).

          ``extensions``    gives additional cache-control extensionsn,
                            such as items like, community="UCI" (14.9.6)

        As recommended by RFC 2616, if ``max_age`` is provided (or
        implicitly set by specifying ``no-cache``, then the ``Expires``
        header is also calculated for HTTP/1.0 clients.  This is done
        """
        assert not has_header(self.headers,'cache-control')
        assert not has_header(self.headers,'expires')
        assert isinstance(max_age,(type(None),int))
        assert isinstance(s_maxage,(type(None),int))
        result = []
        if private is True:
            assert not public and not no_cache and not s_maxage
            self.expires = 0  # Date >= Expires for HTTP/1.0
            result.append('private')
        elif no_cache is True:
            assert not public and not private and not max_age
            self.expires = 0  # Date >= Expires for HTTP/1.0
            result.append('no-cache')
        else:
            assert public is None or public is True
            assert not private and not no_cache
            self.expires = max_age
            result.append('public')
        if no_store:
            result.append('no-store')
        if no_transform:
            result.append('no-transform')
        if max_age is not None:
            result.append('max-age=%d' % max_age)
        if s_maxage is not None:
            result.append('s-maxage=%d' % s_maxage)
        for (k,v) in extensions.items():
            assert '"' not in v
            result.append('%s="%s"' % (k.replace("_","-"),v))
        self.headers.append(('cache-control',", ".join(result)))

    def set_content(self, content):
        self.last_modified = time.time()
        self.content = [content]
        replace_header(self.headers,'content-length', str(len(content)))
        replace_header(self.headers,'last-modified',
                        formatdate(self.last_modified))

    def __call__(self, environ, start_response):
        if self.expires is not None:
            replace_header(self.headers,'expires',
                           formatdate(time.time()+self.expires))

        checkmod = environ.get('HTTP_IF_MODIFIED_SINCE')
        if checkmod:
            try:
                client_clock = mktime_tz(parsedate_tz(checkmod))
            except TypeError:
                return HTTPBadRequest(
                  "Bad Timestamp\n"
                  "Client program did not provide an appropriate "
                  "timestamp for its If-Modified-Since header."
                ).wsgi_application(environ, start_response)
            if client_clock > time.time():
                return HTTPBadRequest((
                  "Clock Time In Future\n"
                  "According to this server, the time provided in "
                  "the If-Modified-Since header (%s) is in the future.\n"
                  "Please check your system clock.") % checkmod
                ).wsgi_application(environ, start_response)
            elif client_clock <= self.last_modified:
                # the client has a recent copy
                start_response('304 Not Modified',[])
                return [''] # empty body

        start_response('200 OK',self.headers)
        return self.content

class FileApp(DataApp):
    """
    Returns an application that will send the file at the given
    filename.  Adds a mime type based on ``mimetypes.guess_type()``.
    See DataApp for the arguments beyond ``filename``.
    """

    def __init__(self, filename, headers=None, **kwargs):
        self.filename = filename
        content_type, content_encoding = mimetypes.guess_type(self.filename)
        if content_type and 'content_type' not in kwargs:
            kwargs['content_type'] = content_type
        if content_encoding and 'content_encoding' not in kwargs:
            kwargs['content_encoding'] = content_encoding
        DataApp.__init__(self, None, headers, **kwargs)

    def update(self):
        stat = os.stat(self.filename)
        if stat.st_mtime == self.last_modified:
            return
        if  stat.st_size < CACHE_SIZE:
            fh = open(self.filename,"rb")
            self.set_content(fh.read())
            fh.close()
        else:
            self.content = None
            replace_header(self.headers, 'content-length',
                           str(stat.st_size))
        self.last_modified = stat.st_mtime

    def __call__(self, environ, start_response):
        self.update()
        if not self.content:
            try:
                file = open(self.filename, 'rb')
            except (IOError, OSError), e:
                exc = httpexceptions.HTTPForbidden(
                    'You are not permitted to view this file (%s)' % e)
                return exc.wsgi_application(
                    environ, start_response)
        retval = DataApp.__call__(self, environ, start_response)
        if retval is not None:
            # cached content, exception, or not-modified
            return retval
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

