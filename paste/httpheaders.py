# (c) 2005 Ian Bicking, Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# Some of this code was funded by http://prometheusresearch.com
"""
HTTP Headers

This contains useful information about various HTTP Headers; eventually
including parsers/constructors for them.  It is modeled after the
HTTPExceptions class; only that a header such as 'Content-Type' is
converted into Python as HTTP_CONTENT_TYPE.  Each HTTPHeader is a string
value, with various attributes describing how that header behaves; the
string value is the "common form" as described in RFC 2616.  It also
overrides sorting so that general headers go first, followed by
request/response headers, and then entity headers.

It is planned that HTTPHeader will grow three methods:

  ``parse()``      This will parse content of the corresponding header
                   and return a dictionary of its components for
                   ``singular`` headers, and a list of dict items for
                   the other headers.

  ``compose()``    This will take N keyword arguments corresponding
                   to the various parts of the header and will produce
                   a well-formed header value.  For example, the
                   cashe_control and content_disposition code in
                   fileapp.py could move here.

  ``__call__()``   This will be similar to ``compose()`` only that it
                   will return a (header, value) tuple suitable for
                   a WSGI ``response_headers`` list.

"""
__all__ = ['get_header','known_headers','HTTPHeader' ]

_headers = {}

def known_headers():
    return _headers.values()

def get_header(name, raiseError=True):
    """
    This function finds the corresponding ``HTTPHeader`` for the
    ``name`` provided.  So that python-style names can be used,
    underscores are converted to dashes before the lookup.
    """
    if isinstance(name,HTTPHeader):
        return name
    retval = _headers.get(name.strip().lower().replace("_","-"))
    if not retval and raiseError:
        raise NameError(name)
    return retval

class HTTPHeader(object):
    """
    HTTP header field names in their normalized "common form" as given
    by their source specification.

    Constructor Arguments:

      ``name``        This is the primary string value of the
                      header name and is meant to reflect the
                      "common form" of the header as provided in
                      its corresponding specification.

      ``category``    The kind of header field, one of:
                      - ``general``
                      - ``request``
                      - ``response``
                      - ``entity``
                      Category is there to follow the RFC's suggestion
                      that general headers go first and entity headers
                      go last.

      ``version``    The version of HTTP with which the header
                     should be recognized (ie, don't send 1.1
                     headers to a 1.0 client).

      ``style``       The style of the header is one of three forms:
                      - ``singular``      (one entry, one value)
                      - ``multi-value``   (one entry, comma separated)
                      - ``multi-entry``   (values have their own entry)
                      Style is intended to inform wrappers about the
                      cardality and storage semantics for the header.

    The collected versions of initialized header instances are immediately
    registered and accessable through the ``get_header`` function.
    """
    #@@: add field-name validation
    def __new__(cls, name, category, version, style):
        self = get_header(name, raiseError=False)
        if self:
            # Allow the registration to happen again, but assert
            # that everything is identical.
            assert self.name == name, \
                "duplicate registration with different capitalization"
            assert self.category == category, \
                "duplicate registration with different category "
            assert self.version == version, \
                "duplicate registration with different HTTP version"
            assert self.style == style, \
                "duplicate registration with different value cardnality"
            assert cls == self.__class__, \
                "duplicate registration with different class"
        else:
            assert version, "registration requires a HTTP Version"
            assert isinstance(version,str), "HTTP version is a string"
            assert category in ('general', 'request', 'response', 'entity')
            assert style    in ('singular', 'multi-value', 'multi-entry')
            self = object.__new__(cls)
            self.name = name
            self.version = version
            self.style = style
            self.category = category
            self._catsort = {'general': 1, 'request': 2, 'response': 2,
                             'entity': 3}[category]
            assert self.name.lower() not in _headers
            _headers[self.name.lower()] = self
        return self

    def __str__(self):
        return self.name

    def __lt__(self, other):
        """
        Re-define sorting so that general headers are first, followed
        by request/response headers, and then entity headers.  The
        list.sort() methods use the less-than operator for this purpose.
        """
        if isinstance(other,HTTPHeader):
            if self._catsort != other._catsort:
                return self._catsort < other._catsort
            return self.name < other.name
        return self.name < other

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.name)
#
# For now, construct a minimalistic version of the field-names; at a
# later date more complicated headers may sprout content constructors.
# This creates WSGI style HTTP_HEADER_NAME instances of HTTPHeader.
#
for (name,              category, version, style,      comment) in \
(("Accept"             ,'request' ,'1.1','multi-value','RFC 2616 $14.1' )
,("Accept-Charset"     ,'request' ,'1.1','multi-value','RFC 2616 $14.2' )
,("Accept-Encoding"    ,'request' ,'1.1','multi-value','RFC 2616 $14.3' )
,("Accept-Language"    ,'request' ,'1.1','multi-value','RFC 2616 $14.4' )
,("Accept-Ranges"      ,'response','1.1','multi-value','RFC 2616 $14.5' )
,("Age"                ,'response','1.1','singular'   ,'RFC 2616 $14.6' )
,("Allow"              ,'entity'  ,'1.0','multi-value','RFC 2616 $14.7' )
,("Authorization"      ,'request' ,'1.0','singular'   ,'RFC 2616 $14.8' )
,("Cache-Control"      ,'general' ,'1.1','multi-value','RFC 2616 $14.9' )
,("Cookie"             ,'request' ,'1.0','multi-value','RFC 2109/Netscape')
,("Connection"         ,'general' ,'1.1','multi-value','RFC 2616 $14.10')
,("Content-Encoding"   ,'entity'  ,'1.0','multi-value','RFC 2616 $14.11')
,("Content-Language"   ,'entity'  ,'1.1','multi-value','RFC 2616 $14.12')
,("Content-Length"     ,'entity'  ,'1.0','singular'   ,'RFC 2616 $14.13')
,("Content-Location"   ,'entity'  ,'1.1','singular'   ,'RFC 2616 $14.14')
,("Content-MD5"        ,'entity'  ,'1.1','singular'   ,'RFC 2616 $14.15')
,("Content-Range"      ,'entity'  ,'1.1','singular'   ,'RFC 2616 $14.16')
,("Content-Type"       ,'entity'  ,'1.0','singular'   ,'RFC 2616 $14.17')
,("Date"               ,'general' ,'1.0','singular'   ,'RFC 2616 $14.18')
,("ETag"               ,'response','1.1','singular'   ,'RFC 2616 $14.19')
,("Expect"             ,'request' ,'1.1','multi-value','RFC 2616 $14.20')
,("Expires"            ,'entity'  ,'1.0','singular'   ,'RFC 2616 $14.21')
,("From"               ,'request' ,'1.0','singular'   ,'RFC 2616 $14.22')
,("Host"               ,'request' ,'1.1','singular'   ,'RFC 2616 $14.23')
,("If-Match"           ,'request' ,'1.1','multi-value','RFC 2616 $14.24')
,("If-Modified-Since"  ,'request' ,'1.0','singular'   ,'RFC 2616 $14.25')
,("If-None-Match"      ,'request' ,'1.1','multi-value','RFC 2616 $14.26')
,("If-Range"           ,'request' ,'1.1','singular'   ,'RFC 2616 $14.27')
,("If-Unmodified-Since",'request' ,'1.1','singular'   ,'RFC 2616 $14.28')
,("Last-Modified"      ,'entity'  ,'1.0','singular'   ,'RFC 2616 $14.29')
,("Location"           ,'response','1.0','singular'   ,'RFC 2616 $14.30')
,("Max-Forwards"       ,'request' ,'1.1','singular'   ,'RFC 2616 $14.31')
,("Pragma"             ,'general' ,'1.0','multi-value','RFC 2616 $14.32')
,("Proxy-Authenticate" ,'response','1.1','multi-value','RFC 2616 $14.33')
,("Proxy-Authorization",'request' ,'1.1','singular'   ,'RFC 2616 $14.34')
,("Range"              ,'request' ,'1.1','multi-value','RFC 2616 $14.35')
,("Referer"            ,'request' ,'1.0','singular'   ,'RFC 2616 $14.36')
,("Retry-After"        ,'response','1.1','singular'   ,'RFC 2616 $14.37')
,("Server"             ,'response','1.0','singular'   ,'RFC 2616 $14.38')
,("Set-Cookie"         ,'response','1.0','multi-entry','RFC 2109/Netscape')
,("TE"                 ,'request' ,'1.1','multi-value','RFC 2616 $14.39')
,("Trailer"            ,'general' ,'1.1','multi-value','RFC 2616 $14.40')
,("Transfer-Encoding"  ,'general' ,'1.1','multi-value','RFC 2616 $14.41')
,("Upgrade"            ,'general' ,'1.1','multi-value','RFC 2616 $14.42')
,("User-Agent"         ,'request' ,'1.0','singular'   ,'RFC 2616 $14.43')
,("Vary"               ,'response','1.1','multi-value','RFC 2616 $14.44')
,("Via"                ,'general' ,'1.1','multi-value','RFC 2616 $14.45')
,("Warning"            ,'general' ,'1.1','multi-entry','RFC 2616 $14.46')
,("WWW-Authenticate"   ,'response','1.0','multi-entry','RFC 2616 $14.47')):
    head = HTTPHeader(name, category, version, style)
    head.__doc__ = comment
    pyname = 'HTTP_' + name.replace("-","_").upper()
    locals()[pyname] = head
    __all__.append(pyname)

