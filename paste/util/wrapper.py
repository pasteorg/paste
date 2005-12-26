# (c) 2005 Ian Bicking, Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# Some of this code was funded by http://prometheusresearch.com
"""
Wrapper

This module contains wrapper objects for WSGI ``environ`` and
``response_headers`` objects.

"""
from paste import httpheaders
from paste.response import replace_header, remove_header, header_value

class EnvironWrapper(object):
    """
    Used to wrap the ``environ`` to provide handy property get/set
    methods for common HTTP headers and for other environment
    variables specified in the WSGI specification.

       wrapped = wrap(environ)
       wrapped.version      -> environ.get('wsgi.version',None)
       wrapped.HTTP_HOST    -> environ.get('HTTP_HOST',None)
       wrapped.REMOTE_USER  -> environ.get('REMOTE_USER',None)

    """
    def __new__(cls, environ):
        assert dict == type(environ)
        assert "wsgi.version" in environ
        self = object.__new__(cls)
        self.environ = environ
        return self
#
# For each WSGI environment variable (and defined HTTP headers),
# add the relevant get/set and attach the property to this class.
#
_proplist = [
  'REQUEST_METHOD', 'SCRIPT_NAME', 'PATH_INFO', 'QUERY_STRING',
  'CONTENT_TYPE', 'CONTENT_LENGTH', 'SERVER_NAME', 'SERVER_PORT',
  'SERVER_PROTOCOL', 'HTTPS', 'SSL_PROTOCOL', 'REMOTE_USER',
  'PATH_TRANSLATED', 'DOCUMENT_ROOT',
  # The 'wsgi.' is stripped for these
  'wsgi.version', 'wsgi.url_scheme', 'wsgi.input', 'wsgi.errors',
  'wsgi.multithread', 'wsgi.multiprocess', 'wsgi.run_once',
  'wsgi.file_wrapper'
]

for name in dir(httpheaders):
    if name.startswith("HTTP_"):
        header = getattr(httpheaders,name)
        if header and 'response' != header.category:
            _proplist.append(name)

for item in _proplist:
    key = item
    if "." in item:
        item = item.split(".")[1]
    def get(self,tmp=key):
        return self.environ.get(tmp,None)
    def set(self,val,tmp=key):
        dict.__setitem__(self.environ,tmp,val)
    setattr(EnvironWrapper, "GET_" + item, get)
    setattr(EnvironWrapper, "SET_" + item, set)
    setattr(EnvironWrapper, item, property(get,set))
del _proplist

class ResponseHeadersWrapper(object):
    """
    Used to wrap the ``response_headers`` to provide handy mechanism
    for dealing with the headers using properties.

       wrapped = wrap(response_headers)
       wrapped.HTTP_CONTENT_ENCODING = 'text/plain'
       etc.

       wrapped.sort()
    """
    def __new__(cls, response_headers):
        assert list == type(response_headers)
        self = object.__new__(cls)
        self.response_headers = response_headers
        return self

for name in dir(httpheaders):
    if not name.startswith("HTTP_"):
        continue
    header = getattr(httpheaders,name)
    if 'request' == header.category or 'multi-entry' == header.style:
        continue
    name = name[5:]
    def get(self,tmp=str(header)):
        return header_value(self.response_headers,tmp)
    def set(self,val,tmp=str(header)):
        return replace_header(self.response_headers,tmp,val)
    setattr(ResponseHeadersWrapper, "GET_" + name, get)
    setattr(ResponseHeadersWrapper, "SET_" + name, set)
    setattr(ResponseHeadersWrapper, name, property(get,set))

def wrap(obj):
    """
    Wraps a WSGI ``environ`` and ``result_headers`` with corresponding
    ``dict`` and ``list`` items that can be passed on up/down stream.
    """
    if isinstance(obj, dict):
        return EnvironWrapper(obj)
    if isinstance(obj, list):
        return ResponseHeadersWrapper(obj)
    assert False, ("The object being wrapped is neither a ``dict`` type "
                   "(which corresponds to a WSGI ``environ``), nor is "
                   "it a ``list`` type (which corresponds to WSGI "
                   "``response_headers``.")

__all__ = ['wrap','EnvironWrapper', 'ResponseHeadersWrapper']
