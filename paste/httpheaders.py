# (c) 2005 Ian Bicking, Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# Some of this code was funded by http://prometheusresearch.com
"""
HTTP Message Headers

This contains general support for message headers as defined by HTTP/1.1
specification, RFC 2616 (in particular section 4.2).  This module
defines the ``HTTPHeader`` class, and corresponding instances for common
headers.  Here are some snippets of how you'd use it:

  environ.get('HTTP_ACCEPT_LANGUAGE')
  -> AcceptLanguage(environ)

    In this usage, the header is passed the ``environ``, and extracts
    the appropriate field-value.  The primary advantage is that a typo
    in the header is a NameError; environ.get('HTTP_ACCEPT_LANGUAGES'),
    by contrast, might be a rather hard bug to track down.

  header_value(response_headers, 'content-type')  # from paste.response
  -> ContentType(response_headers)

     This usage is similar in that typos are easily noticed; but also
     the syntax is the same -- the HTTPHeader can hide the technical
     difference between ``environ`` and ``response_headers`` so that
     your code remains focused on the task.

  response_headers.append(('content-type','text/html'))
  -> ContentType.append(response_headers, 'text/html')

     Although in most cases these two forms have similar result,
     there are a few differences:

     - Since the ContentType header knows that it is a singleton, it
       will raise an exception if already exists in the response_headers

     - The ContentType version uses the recommended RFC capitalization,
       'Content-Type'; while this is easy in this case, it is not easy
       to remember in every case, such as 'ETag' or 'WWW-Authenticate'.

     - The ContentType version can validate the content; while this case
       is easy to inspect that the former is correct -- this isn't
       always true, for example in ContentDisposition or more
       complicated headers.

  remove_header(response_headers, 'content-type')  # from paste.response
  -> ContentType.remove(response_headers)

     No pratical difference other than consistency with the rest
     of the module; same as the ``replace`` method.

  "public, no-store, max-age=%d" % 7*24*60*60
  -> CacheControl(public=True, no_store=True,
                  max_age= CacheControl.ONE_WEEK)

     While the former is the actual header that should be sent, it is
     quite easy to make mistakes in header construction; or specify
     invalid values that look correct but violate the specification.
"""

__all__ = ['get_header', 'HTTPHeader', 'normalize_headers' ]

_headers = {}

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
        raise AssertionError("'%s' is an unknown header" % name)
    return retval

def list_headers(general=True, request=True, response=True, entity=True):
    " list all headers for a given category "
    search = []
    for (bool,strval) in ((general,'general'), (request,'request'),
                         (response,'response'), (entity,'entity')):
        if bool:
            search.append(strval)
    search = tuple(search)
    for head in _headers.values():
        if head.category in search:
            retval.append(head)
    retval.sort()
    return retval

class HTTPHeader(object):
    """
    HTTPHeader instances represent a particular ``field-name`` of an
    HTTP message header. They do not hold a field-value, but instead
    provide operations that work on is corresponding values.  Storage of
    the actual field valies is done with WSGI ``environ`` or
    ``response_headers`` as appropriate.  Typically, a sub-classes that
    represent a specific HTTP header, such as ContentDisposition, are
    singeltons.  Once constructed the HTTPHeader instances themselves
    are immutable and stateless.

    For purposes of documentation a "container" refers to either a
    WSGI ``environ`` dictionary, or a ``response_headers`` list.

    Member variables (and correspondingly constructor arguments).

      ``name``         the ``field-name`` of the header, in "common form"
                       as presented in RFC 2616; e.g. 'Content-Type'

      ``category``     one of 'general', 'request', 'response', or 'entity'

      ``version``      version of HTTP (informational) with which the
                       header should be recognized

      ``sort_order``   sorting order to be applied before sorting on
                       field-name when ordering headers in a response

    Special Methods:

       ``__call__``    The primary method of the HTTPHeader instance is
                       to make it a callable, it takes either a collection,
                       a string value, or keyword arguments and attempts
                       to find/construct a valid field-value

       ``__lt__``      This method is used so that HTTPHeader objects
                       can be sorted in a manner suggested by RFC 2616.

       ``__str__``     The string-value for instances of this class is
                       the ``field-name``.

    Collection Methods:

       ``append()``    appends the given field-value onto a WSGI
                       ``response_headers`` list object

       ``remove()``    removes all field-value occurances of this
                       header in the collection provided

       ``replace()``   replaces (if they exist) all field-value items
                       in the given collection with the value provided

    The collected versions of initialized header instances are immediately
    registered and accessable through the ``get_header`` function.
    """
    #@@: add field-name validation
    def __new__(cls, name, category):
        """
        We use the ``__new__`` operator to ensure that only one
        ``HTTPHeader`` instance exists for each field-name, and to
        register the header so that it can be found/enumerated.
        """
        self = get_header(name, raiseError=False)
        if self:
            # Allow the registration to happen again, but assert
            # that everything is identical.
            assert self.name == name, \
                "duplicate registration with different capitalization"
            assert self.category == category, \
                "duplicate registration with different category"
            assert cls == self.__class__, \
                "duplicate registration with different class"
            return self

        self = object.__new__(cls)
        self.name = name
        self.category = category
        self.sort_order = {'general': 1, 'request': 2,
                           'response': 3, 'entity': 4 }[category]
        _headers[name.lower()] = self
        self._environ_name = 'HTTP_'+ self.name.upper().replace("-","_")
        assert self.version in ('1.1','1.0','0.9')
        assert isinstance(self,(SingleValueHeader,MultiValueHeader,
                                MultiEntryHeader))

    def __str__(self):
        return self.name

    def __lt__(self, other):
        """
        Re-define sorting so that general headers are first, followed
        by request/response headers, and then entity headers.  The
        list.sort() methods use the less-than operator for this purpose.
        """
        if isinstance(other,HTTPHeader):
            if self.sort_order != other.sort_order:
                return self.sort_order < other.sort_order
            return self.name < other.name
        return False

    def __repr__(self):
        return '<HTTPHeader %s>' % self.name

    def construct(**kwargs):
        """
        construct field-value(s) via keyword arguments

        The base implementation of this method simply provides a comma
        separated list of arguments using the convention that a True
        value does not include an equal sign.  It is intended that this
        be specialized for specific headers.
        """
        result = []
        for (k,v) in kwargs.items():
            if v in (None,True):
               result.append(str(k))
            else:
               if isinstance(v,(float,int)):
                  result.append('%s=%s' % (k,v))
               else:
                  result.append('%s="%s"' % (k,v))
        return result

    def format(self, *values):
        """ produce a return value appropriate for this kind of header """
        if not values:
           return None
        raise NotImplementedError()

    def __call__(self, *args, **kwargs):
        """
        This finds/constructs field-value(s) for the given header
        depending upon the arguments:

        - If only keyword arguments are given, then this is equivalent
          to ``format(*construct(**kwargs))``.

        - If the first (and only) argument is a dict, it is assumed
          to be a WSGI ``environ`` and the result of the corresponding
          HTTP_ entry is returned.

        - If the first (and only) argument is a list, it is assumed
          to be a WSGI ``response_headers`` and the field-value(s)
          for this header are collected and returned.

        - In all other cases, the arguments are collected, checked that
          they are string values, possibly verified by the header's
          logic, and returned.

        At this time it is an error to provide keyword arguments if args
        is present (this might change).  It is an error to provide both
        a WSGI object and also string arguments.  It is possible to not
        provide any arguments, in which case none of the above
        constructor functions are called and ``None`` is returned.
        """
        if not args:
            if kwargs:
                return self.format(*self.construct(**kwargs))
            return None
        if list == type(args[0]):
            assert 1 == len(args)
            result = []
            name = self.name.lower()
            for value in [value for header, value in args[0]
                         if header.lower() == name]:
                result.append(value)
            return self.format(*result)
        if dict == type(args[0]):
            assert 1 == len(args) and 'wsgi.version' in args[0]
            value = args[0].get(self._environ_name)
            if value is None:
               return None
            return self.format(value)
        for item in args:
           assert type(item) == str
        return self.format(*args)

class SingleValueHeader(HTTPHeader):
    """
    The field-value is a single value and therefore all results
    constructed or obtained from a collection are asserted to ensure
    that only one result was there.
    """

    def format(self, *values):
        if not values:
           return None
        assert len(values) == 1, "found more than one value for singelton"
        return values[0]

class MultiValueHeader(HTTPHeader):
    """
    This header is multi-valued, however, results can be combined by
    concatinating with a comma, as described by section 4.2 of RFC 2616:

        Multiple message-header fields with the same field-name MAY
        be present in a message if and only if the entire
        field-value for that header field is defined as a
        comma-separated list [i.e., #(values)]. It MUST be possible
        to combine the multiple header fields into one "field-name:
        field-value" pair, without changing the semantics of the
        message, by appending each subsequent field-value to the
        first, each separated by a comma. The order in which header
        fields with the same field-name are received is therefore
        significant to the interpretation of the combined field
        value, and thus a proxy MUST NOT change the order of these
        field values when a message is forwarded.
    """
    def format(self, *values):
        if not values:
           return None
        return ", ".join(values)

class MultiEntryHeader(HTTPHeader):
    """
    This header is multi-valued, but the values should not be combined
    with a comma since the header is not in compliance with RFC 2616
    (Set-Cookie) or which common user-agents do not behave well when the
    header values are combined.
    """
    def format(self, *values):
        if not values:
           return None
        return list(values)

def normalize_headers(response_headers, strict=True):
    """
    This alters the underlying response_headers to use the common
    name for each header; as well as sorting them with general
    headers first, followed by request/response headers, then
    entity headers, and unknown headers last.
    """
    category = {}
    for idx in range(len(response_headers)):
        (key,val) = response_headers[idx]
        head = get_header(key, strict)
        if not head:
            newhead = '-'.join(x.capitalize() for x in \
                               key.replace("_","-").split("-"))
            response_headers[idx] = (newhead,val)
            category[newhead] = 4
            continue
        response_headers[idx] = (str(head),val)
        category[str(head)] = head.sort_order
    def compare(a,b):
        ac = category[a[0]]
        bc = category[b[0]]
        if ac == bc:
            return cmp(a[0],b[0])
        return cmp(ac,bc)
    response_headers.sort(compare)

#
# For now, construct a minimalistic version of the field-names; at a
# later date more complicated headers may sprout content constructors.
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
    cname = name.replace("-","")
    bname = { 'multi-value': 'MultiValueHeader',
              'multi-entry': 'MultiEntryHeader',
              'singular'   : 'SingleValueHeader'}[style]
    exec """\
class %(cname)s(%(bname)s):
    "%(comment)s"
    version = "%(version)s"
%(cname)s('%(name)s','%(category)s');
""" % { 'cname': cname, 'name': name,
        'category': category, 'bname': bname,
        'comment': comment, 'version': version } in globals(), globals()

for head in _headers.values():
    headname = head.name.replace("-","")
    locals()[headname] = head
    __all__.append(headname)
