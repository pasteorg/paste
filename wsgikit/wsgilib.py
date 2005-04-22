from Cookie import SimpleCookie
from cStringIO import StringIO
import mimetypes
import os

def get_cookies(environ):
    """
    Gets a cookie object (which is a dictionary-like object) from the
    request environment; caches this value in case get_cookies is
    called again for the same request.
    """
    header = environ.get('HTTP_COOKIE', '')
    if environ.has_key('paste.cookies'):
        cookies, check_header = environ['paste.cookies']
        if check_header == header:
            return cookies
    cookies = SimpleCookie()
    cookies.load(header)
    environ['paste.cookies'] = (cookies, header)
    return cookies

class add_close:
    """
    An an iterable that iterates over app_iter, then calls
    close_func.
    """
    
    def __init__(self, app_iterable, close_func):
        self.app_iterable = app_iterable
        self.app_iter = iter(app_iterable)
        self.close_func = close_func

    def __iter__(self):
        return self

    def next(self):
        return self.app_iter.next()

    def close(self):
        if hasattr(self.app_iterable, 'close'):
            self.app_iterable.close()
        self.close_func()

def raw_interactive(application, path_info='', **environ):
    """
    Runs the application in a fake environment.
    """
    errors = StringIO()
    basic_environ = {
        'PATH_INFO': str(path_info),
        'SCRIPT_NAME': '',
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '80',
        'REQUEST_METHOD': 'GET',
        'HTTP_HOST': 'localhost:80',
        'CONTENT_LENGTH': '0',
        'wsgi.input': StringIO(''),
        'wsgi.errors': errors,
        'wsgi.version': (1, 0),
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'wsgi.url_scheme': 'http',
        }
    for name, value in environ.items():
        name = name.replace('__', '.')
        basic_environ[name] = value
    if isinstance(basic_environ['wsgi.input'], str):
        basic_environ['wsgi.input'] = StringIO(basic_environ['wsgi.input'])
    output = StringIO()
    data = {}
    def start_response(status, headers):
        data['status'] = status
        data['headers'] = headers
        return output.write
    app_iter = application(basic_environ, start_response)
    try:
        try:
            for s in app_iter:
                output.write(s)
        except TypeError, e:
            # Typically "iteration over non-sequence", so we want
            # to give better debugging information...
            e.args = ((e.args[0] + ' iterable: %r' % app_iter),) + e.args[1:]
            raise
    finally:
        if hasattr(app_iter, 'close'):
            app_iter.close()
    return (data['status'], data['headers'], output.getvalue(),
            errors.getvalue())

def interactive(*args, **kw):
    status, headers, content, errors = raw_interactive(*args, **kw)
    full = StringIO()
    if errors:
        full.write('Errors:\n')
        full.write(errors.strip())
        full.write('\n----------end errors\n')
    full.write(status + '\n')
    for name, value in headers:
        full.write('%s: %s\n' % (name, value))
    full.write('\n')
    full.write(content)
    return full.getvalue()

def construct_url(environ, with_query_string=True):
    """
    Reconstructs the URL from the WSGI environment.
    """
    url = environ['wsgi.url_scheme']+'://'

    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST'].split(':')[0]
    else:
        url += environ['SERVER_NAME']

    if environ['wsgi.url_scheme'] == 'https':
        if environ['SERVER_PORT'] != '443':
           url += ':' + environ['SERVER_PORT']
    else:
        if environ['SERVER_PORT'] != '80':
           url += ':' + environ['SERVER_PORT']

    url += environ.get('SCRIPT_NAME','')
    url += environ.get('PATH_INFO','')
    if with_query_string:
        if environ.get('QUERY_STRING'):
            url += '?' + environ['QUERY_STRING']
    return url

def error_body_response(error_code, message):
    """
    Returns a standard HTML response page for an HTTP error.
    """
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
                   debug_message=None):
    """
    Returns the status, headers, and body of an error response.  Use
    like::

        status, headers, body = wsgilib.error_response(
            '301 Moved Permanently', 'Moved to <a href="%s">%s</a>'
            % (url, url))
        start_response(status, headers)
        return [body]
    """
    if debug_message and environ.get('paste.config', {}).get('debug'):
        message += '\n\n<!-- %s -->' % debug_message
    body = error_body_response(error_code, message)
    headers = [('content-type', 'text/html'),
               ('content-length', str(len(body)))]
    return error_code, headers, body

def send_file(filename):
    """
    Returns an application that will send the file at the given
    filename.  Adds a mime type based on ``mimetypes.guess_type()``.
    """
    # @@: Should test things like last-modified, if-modified-since,
    # etc.
    
    def application(environ, start_response):
        type, encoding = mimetypes.guess_type(filename)
        # @@: I don't know what to do with the encoding.
        size = os.stat(filename).st_size
        try:
            file = open(filename, 'rb')
        except (IOError, OSError), e:
            status, headers, body = error_response(
                '403 Forbidden',
                'You are not permitted to view this file (%s)' % e)
            start_response(status, headers)
            return [body]
        start_response('200 OK',
                       [('content-type', type),
                        ('content-length', str(size))])
        return _FileIter(file)

    return application

class _FileIter:

    def __init__(self, file, blocksize=4096):
        self.file = file
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

def has_header(headers, name):
    """
    Is header named ``name`` present in headers?
    """
    name = name.lower()
    for header, value in headers:
        if header.lower() == name:
            return True
    return False

def header_value(headers, name, collapse=False):
    """
    Returns the header's value, or None if no such header.  If a
    header appears more than once, all the values of the headers
    are joined with ','
    """
    result = [value for header, value in headers
              if header.lower() == name]
    if result:
        return ','.join(result)
    else:
        return None

def path_info_split(path_info):
    """
    Splits off the first segment of the path.  Returns (first_part,
    rest_of_path).  first_part can be None (if PATH_INFO is empty), ''
    (if PATH_INFO is '/'), or a name without any /'s.  rest_of_path
    can be '' or a string starting with /.
    """
    if not path_info:
        return None, ''
    assert path_info.startswith('/'), (
        "PATH_INFO should start with /: %r" % path_info)
    path_info = path_info.lstrip('/')
    if '/' in path_info:
        first, rest = path_info.split('/', 1)
        return first, '/' + rest
    else:
        return path_info, ''
