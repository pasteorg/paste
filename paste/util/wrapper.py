# (c) 2005 Ian Bicking, Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# Some of this code was funded by http://prometheusresearch.com
"""
Wrapper

This module contains wrapper objects for WSGI ``environ`` and
``response_headers`` objects.  The goal is to make these objects
easy to use; but yet maintaining their WSGI compliance.

"""
from paste import httpheaders

class EnvironWrapper(dict):
    """
    Used to wrap the ``environ`` to provide handy property get/set
    methods for common HTTP headers and for other environment
    variables specified in the WSGI specification.

       environ = wrap(environ)
       environ.version     ->  environ.get('wsgi.version',None)
       environ.HTTP_HOST   -> environ.get('HTTP_HOST',None)
       environ.REMOTE_USER -> environ.get('REMOTE_USER',None)

    """
    def __new__(cls, environ):
        if isinstance(environ, EnvironWrapper):
            return environ
        assert isinstance(environ,dict)
        assert "wsgi.version" in environ
        return dict.__new__(cls, environ)

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
for head in dir(httpheaders):
    if head.startswith("HTTP_"):
        _proplist.append(head)

for item in _proplist:
    key = item
    if "." in item:
        item = item.split(".")[1]
    def get(self,tmp=key):
        return dict.get(self,tmp,None)
    def set(self,val,tmp=key):
        dict.__setitem__(self,tmp,val)
        return self
    setattr(EnvironWrapper, "GET_" + item, get)
    setattr(EnvironWrapper, "SET_" + item, set)
    setattr(EnvironWrapper, item, property(get,set))
del _proplist

def wrap(obj):
    """
    Wraps a WSGI ``environ`` and ``result_headers`` with corresponding
    ``dict`` and ``list`` items that can be passed on up/down stream.
    """
    if isinstance(obj, EnvironWrapper):
        return obj
    if isinstance(obj, dict):
        return EnvironWrapper(obj)
    assert False, "Only EnvironWrapper so far"

__all__ = ['wrap','EnvironWrapper']
