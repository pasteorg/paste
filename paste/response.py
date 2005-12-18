############################################################
## Headers
############################################################

class HeaderDict(dict):

    """
    This represents response headers.  It handles the headers as a
    dictionary, with case-insensitive keys.

    Also there is an ``.add(key, value)`` method, which sets the key,
    or adds the value to the current value (turning it into a list if
    necessary).

    For passing to WSGI there is a ``.headeritems()`` method which is
    like ``.items()`` but unpacks value that are lists.  It also
    handles encoding -- all headers are encoded in ASCII (if they are
    unicode).

    @@: Should that encoding be ISO-8859-1 or UTF-8?  I'm not sure
    what the spec says.
    """

    def __getitem__(self, key):
        return dict.__getitem__(self, self.normalize(key))

    def __setitem__(self, key, value):
        dict.__setitem__(self, self.normalize(key), value)

    def __delitem__(self, key):
        dict.__delitem__(self, self.normalize(key))

    def __contains__(self, key):
        return dict.__contains__(self, self.normalize(key))

    has_key = __contains__

    def pop(self, key):
        return dict.pop(self, self.normalize(key))

    def update(self, other):
        for key in other:
            self[self.normalize(key)] = other[key]

    def normalize(self, key):
        return str(key).lower().strip()
        
    def add(self, key, value):
        key = self.normalize(key)
        if key in self:
            if isinstance(self[key], list):
                self[key].append(value)
            else:
                self[key] = [self[key], value]
        else:
            self[key] = value

    def headeritems(self):
        result = []
        for key in self:
            if isinstance(self[key], list):
                for v in self[key]:
                    result.append((key, str(v)))
            else:
                result.append((key, str(self[key])))
        return result

def has_header(headers, name):
    """
    Is header named ``name`` present in headers?
    """
    name = name.lower()
    for header, value in headers:
        if header.lower() == name:
            return True
    return False

def header_value(headers, name):
    """
    Returns the header's value, or None if no such header.  If a
    header appears more than once, all the values of the headers
    are joined with ','
    """
    name = name.lower()
    result = [value for header, value in headers
              if header.lower() == name]
    if result:
        return ','.join(result)
    else:
        return None

def remove_header(headers, name):
    """
    Removes the named header from the list of headers.  Returns the
    value of that header, or None if no header found.  If multiple
    headers are found, only the last one is returned.
    """
    name = name.lower()
    i = 0
    result = None
    while i < len(headers):
        if headers[i][0].lower() == name:
            result = headers[i][1]
            del headers[i]
            continue
        i += 1
    return result

############################################################
## Deprecated methods
############################################################

def error_body_response(error_code, message, __warn=True):
    """
    Returns a standard HTML response page for an HTTP error.
    **Note:** Deprecated
    """
    if __warn:
        warnings.warn(
            'wsgilib.error_body_response is deprecated; use the '
            'wsgi_application method on an HTTPException object '
            'instead', DeprecationWarning, 1)
    return '''\
<html>
  <head>
    <title>%(error_code)s</title>
  </head>
  <body>
  <h1>%(error_code)s</h1>
  %(message)s
  </body>
</html>''' % {
        'error_code': error_code,
        'message': message,
        }


def error_response(environ, error_code, message,
                   debug_message=None, __warn=True):
    """
    Returns the status, headers, and body of an error response.

    Use like::

        status, headers, body = wsgilib.error_response(
            '301 Moved Permanently', 'Moved to <a href="%s">%s</a>'
            % (url, url))
        start_response(status, headers)
        return [body]

    **Note:** Deprecated
    """
    if __warn:
        warnings.warn(
            'wsgilib.error_response is deprecated; use the '
            'wsgi_application method on an HTTPException object '
            'instead', DeprecationWarning, 1)
    if debug_message and environ.get('paste.config', {}).get('debug'):
        message += '\n\n<!-- %s -->' % debug_message
    body = error_body_response(error_code, message, __warn=False)
    headers = [('content-type', 'text/html'),
               ('content-length', str(len(body)))]
    return error_code, headers, body

def error_response_app(error_code, message, debug_message=None,
                       __warn=True):
    """
    An application that emits the given error response.

    **Note:** Deprecated
    """
    if __warn:
        warnings.warn(
            'wsgilib.error_response_app is deprecated; use the '
            'wsgi_application method on an HTTPException object '
            'instead', DeprecationWarning, 1)
    def application(environ, start_response):
        status, headers, body = error_response(
            environ, error_code, message,
            debug_message=debug_message, __warn=False)
        start_response(status, headers)
        return [body]
    return application
