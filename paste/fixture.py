# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

import sys
import random
import urllib
import mimetypes
import time
import cgi
import os
import shutil
import webbrowser
import smtplib
import shlex
from Cookie import SimpleCookie
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import re
try:
    import subprocess
except ImportError:
    pass

from paste import wsgilib
from paste import lint

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

    def get(self, url, params=None, headers={}, extra_environ={},
            status=None, expect_errors=False):
        # Hide from py.test:
        __tracebackhide__ = True
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
        environ.update(extra_environ)
        req = TestRequest(url, environ, expect_errors)
        return self.do_request(req, status=status)

    def post(self, url, params=None, headers={}, extra_environ={},
             status=None, upload_files=None, expect_errors=False):
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
        environ.update(extra_environ)
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
        __tracebackhide__ = True
        if self.cookies:
            c = SimpleCookie()
            for name, value in self.cookies.items():
                c[name] = value
            req.environ['HTTP_COOKIE'] = str(c).split(': ', 1)[1]
        req.environ['paste.testing'] = True
        req.environ['paste.testing_variables'] = {}
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
        for name, value in req.environ['paste.testing_variables']:
            setattr(res, name, value)
        if self.namespace is None:
            # It's annoying to return the response in doctests, as it'll
            # be printed, so we only return it is we couldn't assign
            # it anywhere
            return res

    def check_status(self, status, res):
        __tracebackhide__ = True
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
        in as arguments.

        Equivalent to::

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

class TestFileEnvironment(object):

    """
    This represents an environment in which files will be written, and
    scripts will be run.
    """

    # for py.test
    disabled = True

    def __init__(self, base_path, template_path=None,
                 script_path=None,
                 environ=None, cwd=None, start_clear=True,
                 ignore_paths=None, ignore_hidden=True):
        self.base_path = base_path
        self.template_path = template_path
        if environ is None:
            environ = os.environ.copy()
        self.environ = environ
        if script_path is None:
            script_path = environ.get('PATH', '').split(':')
        self.script_path = script_path
        if cwd is None:
            cwd = base_path
        self.cwd = cwd
        if start_clear:
            self.clear()
        elif not os.path.exists(base_path):
            os.makedirs(base_path)
        self.ignore_paths = ignore_paths or []
        self.ignore_hidden = ignore_hidden

    def run(self, script, *args, **kw):
        """
        Run the command, with the given arguments.  The ``script``
        argument can have space-separated arguments, or you can use
        the positional arguments.

        Keywords allowed are:

        ``expect_error``: (default False)
            Don't raise an exception in case of errors
        ``expect_stderr``: (default ``expect_error``)
            Don't raise an exception if anything is printed to stderr
        ``stdin``: (default ``""``)
            Input to the script
        ``printresult``: (default True)
            Print the result after running

        Returns a ``ProcResponse`` object.
        """
        __tracebackhide__ = True
        expect_error = _popget(kw, 'expect_error', False)
        expect_stderr = _popget(kw, 'expect_stderr', expect_error)
        stdin = _popget(kw, 'stdin', None)
        printresult = _popget(kw, 'printresult', True)
        args = map(str, args)
        assert not kw, (
            "Arguments not expected: %s" % ', '.join(kw.keys()))
        if ' ' in script:
            assert not args, (
                "You cannot give a multi-argument script (%r) "
                "and arguments (%s)" % (script, args))
            script, args = script.split(None, 1)
            args = shlex.split(args)
        script = self.find_exe(script)
        all = [script] + args
        files_before = self.find_files()
        proc = subprocess.Popen(all, stdin=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                cwd=self.cwd,
                                env=self.environ)
        stdout, stderr = proc.communicate(stdin)
        files_after = self.find_files()
        result = ProcResult(
            self, all, stdin, stdout, stderr,
            returncode=proc.returncode,
            files_before=files_before,
            files_after=files_after)
        if printresult:
            print result
            print '-'*40
        if not expect_error:
            result.assert_no_error()
        if not expect_stderr:
            result.assert_no_stderr()
        return result

    def find_exe(self, script_name):
        if self.script_path is None:
            script_name = os.path.join(self.cwd, script_name)
            if not os.path.exists(script_name):
                raise OSError(
                    "Script %s does not exist" % script_name)
            return script_name
        for path in self.script_path:
            fn = os.path.join(path, script_name)
            if os.path.exists(fn):
                return fn
        raise OSError(
            "Script %s could not be found in %s"
            % (script_name, ':'.join(self.script_path)))

    def find_files(self):
        result = {}
        for fn in os.listdir(self.base_path):
            if self._ignore_file(fn):
                continue
            self._find_traverse(fn, result)
        return result

    def _ignore_file(self, fn):
        if fn in self.ignore_paths:
            return True
        if self.ignore_hidden and os.path.basename(fn).startswith('.'):
            return True
        return False

    def _find_traverse(self, path, result):
        full = os.path.join(self.base_path, path)
        if os.path.isdir(full):
            result[path] = FoundDir(self.base_path, path)
            for fn in os.listdir(full):
                fn = os.path.join(path, fn)
                if self._ignore_file(fn):
                    continue
                self._find_traverse(fn, result)
        else:
            result[path] = FoundFile(self.base_path, path)

    def clear(self):
        """
        Delete all the files in the base directory.
        """
        if os.path.exists(self.base_path):
            shutil.rmtree(self.base_path)
        os.mkdir(self.base_path)

    def writefile(self, path, content=None,
                  frompath=None):
        """
        Write a file to the given path.  If ``content`` is given then
        that text is written, otherwise the file in ``frompath`` is
        used.  ``frompath`` is relative to ``self.template_path``
        """
        full = os.path.join(self.base_path, path)
        if not os.path.exists(os.path.dirname(full)):
            os.makedirs(os.path.dirname(full))
        f = open(full, 'wb')
        if content is not None:
            f.write(content)
        if frompath is not None:
            if self.template_path:
                frompath = os.path.join(self.template_path, frompath)
            f2 = open(frompath, 'rb')
            f.write(f2.read())
            f2.close()
        f.close()
        return FoundFile(self.base_path, path)

class ProcResult(object):

    """
    Represents the results of running a command in
    ``TestFileEnvironment``.

    Attributes to pay particular attention to:

    ``stdout``, ``stderr``:
        What is produced
        
    ``files_created``, ``files_deleted``, ``files_updated``:
        Dictionaries mapping filenames (relative to the ``base_dir``)
        to ``FoundFile`` or ``FoundDir`` objects.
    """

    def __init__(self, test_env, args, stdin, stdout, stderr,
                 returncode, files_before, files_after):
        self.test_env = test_env
        self.args = args
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.files_before = files_before
        self.files_after = files_after
        self.files_deleted = {}
        self.files_updated = {}
        self.files_created = files_after.copy()
        for path, f in files_before.items():
            if path not in files_after:
                self.files_deleted[path] = f
                continue
            del self.files_created[path]
            if f.mtime < files_after[path].mtime:
                self.files_updated[path] = files_after[path]

    def assert_no_error(self):
        __tracebackhide__ = True
        assert self.returncode is 0, (
            "Script returned code: %s" % self.returncode)

    def assert_no_stderr(self):
        __tracebackhide__ = True
        if self.stderr:
            print 'Error output:'
            print self.stderr
            raise AssertionError("stderr output not expected")

    def __str__(self):
        s = ['Script result: %s' % ' '.join(self.args)]
        if self.returncode:
            s.append('  return code: %s' % self.returncode)
        if self.stderr:
            s.append('-- stderr: --------------------')
            s.append(self.stderr)
        if self.stdout:
            s.append('-- stdout: --------------------')
            s.append(self.stdout)
        for name, files, show_size in [
            ('created', self.files_created, True),
            ('deleted', self.files_deleted, True),
            ('updated', self.files_updated, True)]:
            if files:
                s.append('-- %s: -------------------' % name)
                files = files.items()
                files.sort()
                last = ''
                for path, f in files:
                    t = '  %s' % _space_prefix(last, path, indent=4,
                                               include_sep=False)
                    last = path
                    if show_size and f.size != 'N/A':
                        t += '  (%s bytes)' % f.size
                    s.append(t)
        return '\n'.join(s)

class FoundFile(object):

    file = True
    dir = False

    def __init__(self, base_path, path):
        self.base_path = base_path
        self.path = path
        self.full = os.path.join(base_path, path)
        self.stat = os.stat(self.full)
        self.mtime = self.stat.st_mtime
        self.size = self.stat.st_size
        self._bytes = None

    def bytes__get(self):
        if self._bytes is None:
            f = open(self.full, 'rb')
            self._bytes = f.read()
            f.close()
        return self._bytes
    bytes = property(bytes__get)

    def __contains__(self, s):
        return s in self.bytes

    def mustcontain(self, s):
        __tracebackhide__ = True
        bytes = self.bytes
        if s not in bytes:
            print 'Could not find %r in:' % s
            print bytes
            assert s in bytes

    def __repr__(self):
        return '<%s %s:%s>' % (
            self.__class__.__name__,
            self.base_path, self.path)

class FoundDir(object):

    file = False
    dir = True

    def __init__(self, base_path, path):
        self.base_path = base_path
        self.path = path
        self.full = os.path.join(base_path, path)
        self.size = 'N/A'
        self.mtime = 'N/A'

    def __repr__(self):
        return '<%s %s:%s>' % (
            self.__class__.__name__,
            self.base_path, self.path)

def _popget(d, key, default=None):
    """
    Pop the key if found (else return default)
    """
    if key in d:
        return d.pop(key)
    return default

def _space_prefix(pref, full, sep=None, indent=None, include_sep=True):
    """
    Anything shared by pref and full will be replaced with spaces
    in full, and full returned.
    """
    if sep is None:
        sep = os.path.sep
    pref = pref.split(sep)
    full = full.split(sep)
    padding = []
    while pref and full and pref[0] == full[0]:
        if indent is None:
            padding.append(' ' * (len(full[0]) + len(sep)))
        else:
            padding.append(' ' * indent)
        full.pop(0)
        pref.pop(0)
    if padding:
        if include_sep:
            return ''.join(padding) + sep + sep.join(full)
        else:
            return ''.join(padding) + sep.join(full)
    else:
        return sep.join(full)

def setup_module(module=None):
    """
    This is used by py.test if it is in the module, so you can
    import this directly.

    Use like::

        from paste.tests.fixture import setup_module
    """
    if module is None:
        # The module we were called from must be the module...
        module = sys._getframe().f_back.f_globals['__name__']
    if isinstance(module, (str, unicode)):
        module = sys.modules[module]
    if hasattr(module, 'reset_state'):
        module.reset_state()

