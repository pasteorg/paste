import sys
import random
import urllib
import mimetypes
import time
import cgi
import os
import webbrowser
import smtplib
from Cookie import SimpleCookie
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import re
#from py.test.collect import Module, PyCollector
from paste.util import thirdparty
doctest = thirdparty.load_new_module('doctest', (2, 4))
from paste import wsgilib
from paste import lint
from paste import pyconfig
from paste import CONFIG
from paste import server

def tempnam_no_warning(*args):
    """
    An os.tempnam with the warning turned off, because sometimes
    you just need to use this and don't care about the stupid
    security warning.
    """
    return os.tempnam(*args)

class NoDefault:
    pass

class Dummy(object):

    def __init__(self, **kw):
        for name, value in kw.items():
            if name.startswith('method_'):
                name = name[len('method_'):]
                value = DummyMethod(value)
            setattr(self, name, value)

class DummyMethod(object):

    def __init__(self, return_value):
        self.return_value = return_value

    def __call__(self, *args, **kw):
        return self.return_value
                
def capture_stdout(func, *args, **kw):
    newstdout = StringIO()
    oldstdout = sys.stdout
    sys.stdout = newstdout
    try:
        result = func(*args, **kw)
    finally:
        sys.stdout = oldstdout
    return result, newstdout.getvalue()

def assert_error(func, *args, **kw):
    kw.setdefault('error', Exception)
    kw.setdefault('text_re', None)
    error = kw.pop('error')
    text_re = kw.pop('text_re')
    if text_re and isinstance(text_re, str):
        real_text_re = re.compile(text_re, re.S)
    else:
        real_text_re = text_re
    try:
        value = func(*args, **kw)
    except error, e:
        if real_text_re and not real_text_re.search(str(e)):
            assert False, (
                "Exception did not match pattern; exception:\n  %r;\n"
                "pattern:\n  %r"
                % (str(e), text_re))
    except Exception, e:
        assert False, (
            "Exception type %s should have been raised; got %s instead (%s)"
            % (error, e.__class__, e))
    else:
        assert False, (
            "Exception was expected, instead successfully returned %r"
            % (value))

def sorted(l):
    l = list(l)
    l.sort()
    return l

class Dummy_smtplib(object):

    existing = None

    def __init__(self, server):
        assert not self.existing, (
            "smtplib.SMTP() called again before Dummy_smtplib.existing.reset() "
            "called.")
        self.server = server
        self.open = True
        self.__class__.existing = self

    def quit(self):
        assert self.open, (
            "Called %s.quit() twice" % self)
        self.open = False

    def sendmail(self, from_address, to_addresses, msg):
        self.from_address = from_address
        self.to_addresses = to_addresses
        self.message = msg

    def install(cls):
        smtplib.SMTP = cls

    install = classmethod(install)

    def reset(self):
        assert not self.open, (
            "SMTP connection not quit")
        self.__class__.existing = None
        
class FakeFilesystem(object):

    def __init__(self):
        self.files = {}

    def make_file(self, filename, content):
        self.files[filename] = content

    def open(self, filename, mode='r'):
        if not self.files.has_key(filename):
            raise IOError("[FakeFS] No such file or directory: %r" % filename)


class FakeFile(object):

    def __init__(self, filename, content=None):
        self.filename = filename
        self.content = content

    def open(self, mode):
        if mode == 'r' or mode == 'rb':
            if self.content is None:
                raise IOError("[FakeFS] No such file or directory: %r"
                              % self.filename)
            return ReaderFile(self)
        elif mode == 'w' or mode == 'wb':
            return WriterFile(self)
        else:
            assert 0, "Mode %r not yet implemented" % mode

class ReaderFile(object):

    def __init__(self, fp):
        self.file = fp
        self.stream = StringIO(self.file.content)
        self.open = True

    def read(self, *args):
        return self.stream.read(*args)

    def close(self):
        assert self.open, (
            "Closing open file")
        self.open = False

class WriterFile(object):

    def __init__(self, fp):
        self.file = fp
        self.stream = StringIO()
        self.open = True

    def write(self, arg):
        self.stream.write(arg)

    def close(self):
        assert self.open, (
            "Closing an open file")
        self.open = False
        
        
    
class AppError(Exception):
    pass

class TestApp(object):

    # for py.test
    disabled = True

    def __init__(self, app, namespace=None, relative_to=None):
        if isinstance(app, (str, unicode)):
            from paste.deploy import loadapp
            # @@: Should pick up relative_to from calling module's
            # __file__
            app = loadapp(app, relative_to=relative_to)
        self.app = app
        self.namespace = namespace
        self.relative_to = relative_to
        self.reset()

    def reset(self):
        self.cookies = {}

    def make_environ(self):
        environ = {}
        environ['paste.throw_errors'] = True
        return environ

    def get(self, url, params=None, headers={},
            status=None,
            expect_errors=False):
        if params:
            if isinstance(params, dict):
                params = urllib.urlencode(params)
            if '?' in url:
                url += '&'
            else:
                url += '?'
            url += params
        environ = self.make_environ()
        for header, value in headers.items():
            environ['HTTP_%s' % header.replace('-', '_').upper()] = value
        if '?' in url:
            url, environ['QUERY_STRING'] = url.split('?', 1)
        req = TestRequest(url, environ, expect_errors)
        return self.do_request(req, status=status)

    def post(self, url, params=None, headers={}, status=None,
             upload_files=None, expect_errors=False):
        environ = self.make_environ()
        if params and isinstance(params, dict):
            params = urllib.urlencode(params)
        if upload_files:
            params = cgi.parse_qsl(params, keep_blank_values=True)
            content_type, params = self.encode_multipart(
                params, upload_files)
            environ['CONTENT_TYPE'] = content_type
        environ['CONTENT_LENGTH'] = str(len(params))
        environ['REQUEST_METHOD'] = 'POST'
        environ['wsgi.input'] = StringIO(params)
        for header, value in headers.items():
            environ['HTTP_%s' % header.replace('-', '_').upper()] = value
        req = TestRequest(url, environ, expect_errors)
        return self.do_request(req, status=status)
            
    def encode_multipart(self, params, files):
        """
        Encodes a set of parameters (typically a name/value list) and
        a set of files (a list of (name, filename, file_body)) into a
        typical POST body, returning the (content_type, body).
        """
        boundary = '----------a_BoUnDaRy%s$' % random.random()
        lines = []
        for key, value in params:
            lines.append('--'+boundary)
            lines.append('Content-Disposition: form-data; name="%s"' % key)
            lines.append('')
            lines.append(value)
        for file_info in files:
            key, filename, value = self.get_file_info(file_info)
            lines.append('--'+boundary)
            lines.append('Content-Disposition: form-data; name="%s"; filename="%s"'
                         % (key, filename))
            fcontent = mimetypes.guess_type(filename)[0]
            lines.append('Content-Type: %s' %
                         fcontent or 'application/octet-stream')
            lines.append('')
            lines.append(value)
        lines.append('--' + boundary + '--')
        lines.append('')
        body = '\r\n'.join(lines)
        content_type = 'multipart/form-data; boundary=%s' % boundary
        return content_type, body

    def get_file_info(self, file_info):
        if len(file_info) == 2:
            # It only has a filename
            filename = file_info[2]
            if self.relative_to:
                filename = os.path.join(self.relative_to, filename)
            f = open(filename, 'rb')
            content = f.read()
            f.close()
            return (file_info[0], filename, content)
        elif len(file_info) == 3:
            return file_info
        else:
            raise ValueError(
                "upload_files need to be a list of tuples of (fieldname, "
                "filename, filecontent) or (fieldname, filename); "
                "you gave: %r"
                % repr(file_info)[:100])

    def do_request(self, req, status):
        if self.cookies:
            c = SimpleCookie()
            for name, value in self.cookies.items():
                c[name] = value
            req.environ['HTTP_COOKIE'] = str(c).split(': ', 1)[1]
        app = lint.middleware(self.app)
        old_stdout = sys.stdout
        out = StringIO()
        try:
            sys.stdout = out
            start_time = time.time()
            raw_res = wsgilib.raw_interactive(app, req.url, **req.environ)
            end_time = time.time()
        finally:
            sys.stdout = old_stdout
            sys.stderr.write(out.getvalue())
        res = self.make_response(raw_res, end_time - start_time)
        res.request = req
        if self.namespace is not None:
            self.namespace['res'] = res
        if not req.expect_errors:
            self.check_status(status, res)
            self.check_errors(res)
        for header in res.all_headers('set-cookie'):
            c = SimpleCookie(header)
            for key, morsel in c.items():
                self.cookies[key] = morsel.value
        if self.namespace is None:
            # It's annoying to return the response in doctests, as it'll
            # be printed, so we only return it is we couldn't assign
            # it anywhere
            return res

    def check_status(self, status, res):
        if status == '*':
            return
        if status is None:
            if res.status == 200 or (
                res.status >= 300 and res.status < 400):
                return
            raise AppError(
                "Bad response: %s (not 200 OK or 3xx redirect)"
                % res.full_status)
        if status != res.status:
            raise AppError(
                "Bad response: %s (not %s)" % (res.full_status, status))

    def check_errors(self, res):
        if res.errors:
            raise AppError(
                "Application had errors logged:\n%s" % res.errors)
        
    def make_response(self, (status, headers, body, errors), total_time):
        return TestResponse(self, status, headers, body, errors,
                            total_time)

class TestResponse(object):

    # for py.test
    disabled = True

    def __init__(self, test_app, status, headers, body, errors,
                 total_time):
        self.test_app = test_app
        self.status = int(status.split()[0])
        self.full_status = status
        self.headers = headers
        self.body = body
        self.errors = errors
        self._normal_body = None
        self.time = total_time
        
    def header(self, name, default=NoDefault):
        """
        Returns the named header; an error if there is not exactly one
        matching header (unless you give a default -- always an error
        if there is more than one header)
        """
        found = None
        for cur_name, value in self.headers:
            if cur_name.lower() == name.lower():
                assert not found, (
                    "Ambiguous header: %s matches %r and %r"
                    % (name, found, value))
                found = value
        if found is None:
            if default is NoDefault:
                raise KeyError(
                    "No header found: %r (from %s)"
                    % (name, ', '.join([n for n, v in self.headers])))
            else:
                return default
        return found

    def all_headers(self, name):
        """
        Gets all headers, returns as a list
        """
        found = []
        for cur_name, value in self.headers:
            if cur_name.lower() == name.lower():
                found.append(value)
        return found

    def follow(self, **kw):
        """
        If this request is a redirect, follow that redirect.
        """
        assert self.status >= 300 and self.status < 400, (
            "You can only follow redirect responses (not %s)"
            % self.full_status)
        location = self.header('location')
        type, rest = urllib.splittype(location)
        host, path = urllib.splithost(rest)
        # @@: We should test that it's not a remote redirect
        return self.test_app.get(location, **kw)

    _normal_body_regex = re.compile(r'[ \n\r\t]+')

    def normal_body__get(self):
        if self._normal_body is None:
            self._normal_body = self._normal_body_regex.sub(
                ' ', self.body)
        return self._normal_body

    normal_body = property(normal_body__get)

    def __contains__(self, s):
        """
        A response 'contains' a string if it is present in the body
        of the response.  Whitespace is normalized when searching
        for a string.
        """
        return (self.body.find(s) != -1
                or self.normal_body.find(s) != -1)

    def mustcontain(self, *strings):
        """
        Assert that the response contains all of the strings passed
        in as arguments.  Equivalent to::

            assert string in res
        """
        for s in strings:
            if not s in self:
                print >> sys.stderr, "Actual response (no %r):" % s
                print >> sys.stderr, self
                raise IndexError(
                    "Body does not contain string %r" % s)

    def __repr__(self):
        return '<Response %s %r>' % (self.full_status, self.body[:20])

    def __str__(self):
        simple_body = '\n'.join([l for l in self.body.splitlines()
                                 if l.strip()])
        return 'Response: %s\n%s\n%s' % (
            self.status,
            '\n'.join(['%s: %s' % (n, v) for n, v in self.headers]),
            simple_body)

    def showbrowser(self):
        """
        Show this response in a browser window (for debugging purposes,
        when it's hard to read the HTML).
        """
        fn = tempnam_no_warning(None, 'paste-fixture') + '.html'
        f = open(fn, 'wb')
        f.write(self.body)
        f.close()
        url = 'file:' + fn.replace(os.sep, '/')
        webbrowser.open_new(url)
        
class TestRequest(object):

    # for py.test
    disabled = True

    def __init__(self, url, environ, expect_errors=False):
        self.url = url
        self.environ = environ
        if environ.get('QUERY_STRING'):
            self.full_url = url + '?' + environ['QUERY_STRING']
        else:
            self.full_url = url
        self.expect_errors = expect_errors

def setup_module(module=None):
    """
    This is used by py.test if it is in the module, so do::

        from paste.tests.fixture import setup_module

    to enable this.  This adds an ``app`` and ``CONFIG`` object to the
    module.  If there is a function ``reset_state`` in your module
    then that is also called.
    """
    if module is None:
        # The module we were called from must be the module...
        module = sys._getframe().f_back.f_globals['__name__']
    if isinstance(module, (str, unicode)):
        module = sys.modules[module]
    if hasattr(module, 'reset_state'):
        module.reset_state()

