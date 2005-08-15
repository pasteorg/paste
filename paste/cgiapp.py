"""
Application that runs a CGI script.
"""
import os
import subprocess

__all__ = ['CGIError', 'CGIApplication']

class CGIError(Exception):
    pass

class CGIApplication(object):

    """
    This object acts as a proxy to a CGI application.  You pass in the
    script path (``script``), an optional path to search for the
    script (if the name isn't absolute) (``path``).  If you don't give
    a path, then ``$PATH`` will be used.
    """

    def __init__(self, script, path=None,
                 include_os_environ=True):
        self.script_filename = script
        if isinstance(path, (str, unicode)):
            path = [path]
        if path is None:
            path = os.environ.get('PATH', '').split(':')
        self.path = path
        if os.path.abspath(script) != script:
            # relative path
            for path_dir in self.path:
                if os.path.exists(os.path.join(path_dir, script)):
                    self.script = os.path.join(path_dir, script)
                    break
            else:
                raise CGIError(
                    "Script %r not found in path %r"
                    % (script, self.path))
        else:
            self.script = script
        self.include_os_environ = include_os_environ

    def __call__(self, environ, start_response):
        if self.include_os_environ:
            cgi_environ = os.environ.copy()
        else:
            cgi_environ = {}
        for name in environ:
            # Should unicode values be encoded?
            if (name.upper() == name
                and isinstance(environ[name], str)):
                cgi_environ[name] = environ[name]
        # Default status in CGI:
        status = '200 OK'
        headers = []
        proc = subprocess.Popen(
            [self.script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=cgi_environ,
            cwd=os.path.dirname(self.script),
            )
        proc.stdin.write(environ['wsgi.input'].read())
        stdout = proc.stdout
        while 1:
            line = stdout.readline()
            line = line.rstrip('\n').rstrip('\r')
            if not line:
                break
            if ':' not in line:
                raise CGIError(
                    "Bad header line: %r" % line)
            name, value = line.split(':', 1)
            value = value.lstrip()
            name = name.strip()
            if name.lower() == 'status':
                status = value
            else:
                headers.append((name, value))
        writer = start_response(status, headers)
        while 1:
            data = stdout.read(4096)
            if not data:
                break
            writer(data)
        environ['wsgi.errors'].write(proc.stderr.read())
        return []
