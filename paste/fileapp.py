# (c) 2005 Ian Bicking, Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""
This module handles sending static content such as in-memory data or
files.  At this time it has cache helpers and understands the
if-modified-since request header.
"""

import os, time
import mimetypes
import httpexceptions
from response import has_header, replace_header, header_value
from rfc822 import formatdate, parsedate_tz, mktime_tz
from httpexceptions import HTTPBadRequest

CACHE_SIZE = 4096
BLOCK_SIZE = 4096 * 16
U_MIMETYPE = 'application/octet-stream'

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

    ``cache_control()``

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
        self.content_length = None
        self.last_modified = 0
        self.headers = headers or []
        for (k,v) in kwargs.items():
            hk = k.replace("_","-")
            if not headers or not has_header(self.headers,hk):
                self.headers.append((hk,v))
        replace_header(self.headers,'accept-ranges','bytes')
        if not has_header(self.headers,'content-type'):
            self.headers.append(('content-type',U_MIMETYPE))
        if content:
            self.set_content(content)

    def cache_control(self, public=None, private=None, no_cache=None,
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

        As recommended by RFC 2616, if ``max_age`` is provided, then
        then the ``Expires`` header is also calculated for HTTP/1.0
        clients and proxies.   For ``no-cache`` and for ``private``
        cases, we either do not want the response cached or do not want
        any response accidently returned to other users; so to prevent
        this case, we set the ``Expires`` header to the time of the
        request, signifying to HTTP/1.0 transports that the content
        isn't to be cached.  If you are using SSL, your communication
        is already "private", so to work with HTTP/1.0 browsers,
        consider specifying your cache as public as the distinction
        between public and private is moot for this case.
        """
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
            assert 'age' not in k
            assert '"' not in v
            result.append('%s="%s"' % (k.replace("_","-"),v))
        replace_header(self.headers,'cache-control',", ".join(result))
        return self

    def set_content(self, content):
        assert content is not None
        self.last_modified = time.time()
        self.content = content
        self.content_length = len(content)
        replace_header(self.headers,'last-modified',
                        formatdate(self.last_modified))
        return self

    def content_disposition(self, attachment=None, inline=None,
                            filename=None):
        """
        Sets the ``Content-Disposition`` header according to RFC 1806,
        as specified in 19.5.1 of RFC 2616.  Note that this is not an
        approved HTTP/1.1 header, but it is very common and useful.

          ``attachment``    if True, this specifies that the content
                            should not be shown in the browser and
                            should be handled externally, even if the
                            browser could render the content

          ``inline``        exclusive with attachment; indicates that the
                            content should be rendered in the browser if
                            possible, but otherwise it should be handled
                            externally

          Only one of the above 2 may be True.  If both are None, then
          the disposition is assumed to be an ``attachment``. These are
          distinct fields since support for field enumeration may be
          added in the future.

          ``filename``      the filename parameter, if any, to be reported;
                            if this is None, then the current object's
                            'filename' attribute is used

          If filename is provided, and Content-Type is not set or is
          'application/octet-stream', then the mimetypes.guess is used
          to upgrade the Content-Type setting.
        """
        assert not (attachment and inline)
        if filename is None:
            filename = getattr(self,'filename',None)
        else:
            if header_value(self.headers,'content-type') == U_MIMETYPE:
                content_type, _ = mimetypes.guess_type(filename)
                replace_header(self.headers,'content-type',content_type)
        result = []
        if inline is True:
            assert not attachment
            result.append('inline')
        else:
            assert not inline
            result.append('attachment')
        if filename:
            assert '"' not in filename
            filename = filename.split("/")[-1]
            filename = filename.split("\\")[-1]
            result.append('filename="%s"' % filename)
        replace_header(self.headers,'content-disposition',"; ".join(result))
        return self

    def __call__(self, environ, start_response):
        headers = self.headers[:]
        if self.expires is not None:
            replace_header(headers,'expires',
                           formatdate(time.time()+self.expires))

        checkmod = environ.get('HTTP_IF_MODIFIED_SINCE')
        if checkmod:
            try:
                client_clock = mktime_tz(parsedate_tz(checkmod.strip()))
            except TypeError:
                return HTTPBadRequest((
                  "Client program provided an ill-formed timestamp for\r\n"
                  "its If-Modified-Since header:\r\n"
                  "  %s\r\n") % checkmod
                ).wsgi_application(environ, start_response)
            if client_clock > time.time():
                return HTTPBadRequest((
                  "Please check your system clock.\r\n"
                  "According to this server, the time provided in the\r\n"
                  "If-Modified-Since header is in the future:\r\n"
                  "  %s\r\n") % checkmod
                ).wsgi_application(environ, start_response)
            elif client_clock <= self.last_modified:
                # the client has a recent copy
                headers = []
                for head in ('etag','content-location','vary',
                             'expires','cache-control'):
                    value = header_value(self.headers,head)
                    if value:
                        headers.apppend((head, value))
                start_response('304 Not Modified',headers)
                return [''] # empty body

        (lower,upper) = (0, self.content_length - 1)
        if 'HTTP_RANGE' in environ:
            print environ['HTTP_RANGE']
            range = environ['HTTP_RANGE'].split(",")[0]
            range = range.strip().lower().replace(" ","")
            if not range.startswith("bytes=") or 1 != range.count("-"):
                return HTTPBadRequest((
                  "A malformed range request was given.\r\n"
                  "  Range: %s\r\n") % range
                ).wsgi_application(environ, start_response)
            (lower,upper) = range[len("bytes="):].split("-")
            upper = upper and int(upper) or (self.content_length - 1)
            lower = lower and int(lower) or 0
            if upper >= self.content_length or lower >= self.content_length:
                return HTTPBadRequest((
                  "Range request was made beyond the end of the content,\r\n"
                  "which is %s long.\r\n  Range: %s\r\n") % (
                     self.content_length, range)
                ).wsgi_application(environ, start_response)

        content_length = 1 + (upper - lower)
        replace_header(headers,'content-length', str(content_length))
        replace_header(headers,'content-range',
            "%d-%d/%d" % (lower, upper, self.content_length))

        start_response('200 OK',headers)
        if self.content is not None:
            return [self.content[lower:upper+1]]
        assert self.__class__ != DataApp, "DataApp must call set_content"
        return (lower, content_length)

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

    def update(self, force=False):
        stat = os.stat(self.filename)
        if not force and stat.st_mtime == self.last_modified:
            return
        if stat.st_size < CACHE_SIZE:
            fh = open(self.filename,"rb")
            self.set_content(fh.read())
            fh.close()
        else:
            self.content = None
            self.content_length = stat.st_size
        self.last_modified = stat.st_mtime

    def __call__(self, environ, start_response):
        if 'max-age=0' in environ.get("HTTP_CACHE_CONTROL",''):
            self.update(force=True) # RFC 2616 13.2.6
        else:
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
        if isinstance(retval,list):
            # cached content, exception, or not-modified
            return retval
        (lower, content_length) = retval
        file.seek(lower)
        return _FileIter(file, size=content_length)

class _FileIter:

    def __init__(self, file, block_size=None, size=None):
        self.file = file
        self.size = size
        self.block_size = block_size or BLOCK_SIZE

    def __iter__(self):
        return self

    def next(self):
        chunk_size = self.block_size
        if self.size is not None:
            if chunk_size > self.size:
                chunk_size = self.size
            self.size -= chunk_size
        data = self.file.read(chunk_size)
        if not data:
            raise StopIteration
        return data

    def close(self):
        self.file.close()

