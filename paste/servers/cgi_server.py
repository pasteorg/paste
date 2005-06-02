import os
import sys
import commands
from paste import server

def serve(conf, app):
    replacements = {}
    replacements['default_config_fn'] = os.path.abspath(
        server.default_config_fn)

    # Ideally, other_conf should be any options that came from the
    # command-line.
    # @@: This assumes too much about the ordering of namespaces.
    other_conf = dict(conf.namespaces[-2])
    # Not a good idea to let 'verbose' through, but this doesn't really
    # stop any sourced configs from setting it either...
    if other_conf.has_key('verbose'):
        del other_conf['verbose']
    replacements['other_conf'] = other_conf
    replacements['extra_sys_path'] = find_extra_sys_path()

    template_fn = os.path.join(os.path.dirname(__file__),
                               'server_script_template.py.txt')
    template = open(template_fn).read()
    for name, value in replacements.items():
        template = template.replace('@@' + name + '@@', repr(value))

    print "#!%s" % sys.executable
    print template
    print "if __name__ == '__main__':"
    print "    from paste.servers.cgi_wsgi import run_with_cgi"
    print "    run_with_cgi(app, redirect_stdout=True)"

description = """\
A 'server' that creates a CGI script that you can use to invoke your
application.
"""

help = """\
Typically you would use this like:

  %prog --server=cgi > .../cgi-bin/myapp.cgi
  chmod +x .../cgi-bin/myapp.cgi
"""

def find_extra_sys_path():
    """
    Tries to find all the items on sys.path that wouldn't be there
    normally.
    """
    args = [sys.executable, "-c", "import sys; print sys.path"]
    old_keys = {}
    for key, value in os.environ.items():
        if key.startswith('PYTHON'):
            old_keys[key] = value
            del os.environ[key]
    result = commands.getoutput('%s -c "import sys; print sys.path"'
                                % sys.executable)
    os.environ.update(old_keys)
    bare_sys_path = eval(result)
    extra = [path for path in sys.path
             if path not in bare_sys_path]
    return extra

    
