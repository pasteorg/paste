#!/usr/bin/env python
"""
A generic Paste server, useable for multiple backends
"""

help_message = """\
usage: %(program)s [OPTIONS] servername
Runs a server with the given options.  The following servers are available:

OPTIONS
-f FILENAME
--config-file=FILENAME
    The configuration file (default: no configuration).
-h  Help
--server=NAME
    Name is one of:
      wsgiutils:
        Runs an HTTP server.  Use --port for the port (default: 8080),
        and --host for the interface (default: all interfaces).
      cgi:
        Creates a CGI script -- outputs the script to stdout.
--publish-dir=PATH
    Serves Webware servlets (or other applications) out of PATH
--debug  -D
    Turn on debugging (shows errors in the browser)
--verbose  -v
    Be verbose
"""

import sys
import os
from paste import reloader
from paste import wsgilib

# This way you can run this out of a checkout, and we'll fix up
# the path...
try:
    here = os.path.normpath(os.path.abspath(__file__))
except NameError:
    here = os.path.normpath(os.path.abspath(sys.argv[0]))
try:
    import paste
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(here)))
    import paste
paste_path = os.path.normpath(
    os.path.dirname(os.path.abspath(paste.__file__)))

if os.path.dirname(here) != paste_path:
    sys.stderr.write(
        'Warning: server.py is running out of %s, but paste is loaded '
        'out of %s\n' % (here, paste_path))

from paste.pyconfig import Config
from paste.configmiddleware import config_middleware
from paste.webkit import wsgiwebkit
from paste.util import thirdparty

servers = {}

default_ops = {
    'port': 8080,
    'host': 'localhost',
    'verbose': False,
    'quiet': False,
    'reload': False,
    }

reloader_environ_key = 'WSGI_RELOADER_SHOULD_RUN'

default_config_fn = os.path.join(os.path.dirname(__file__),
                                 'default_config.conf')

def load_commandline(args, allow_reload=True):
    conf = Config()
    # We use conf.verbose early, so we set it now:
    conf.load_dict(default_ops, default=True)
    args = conf.load_commandline(
        args, bool_options=['help', 'verbose', 'reload', 'debug', 'quiet',
                            'no_verbose'],
        aliases={'h': 'help', 'v': 'verbose', 'f': 'config_file',
                 'D': 'debug', 'q': 'quiet'})
    if conf.get('help'):
        print help()
        return None, 0
    if conf.get('no_verbose'):
        conf['verbose'] = False
    load_conf(conf, default_config_fn, True)
    reloader.watch_file(default_config_fn)
    if not conf.get('no_server_conf') and os.path.exists('server.conf'):
        load_conf(conf, 'server.conf', True)
        reloader.watch_file('server.conf')
    if conf.get('config_file'):
        load_conf(conf, conf['config_file'], True)
        reloader.watch_file(conf['config_file'])
    if conf['quiet']:
        conf['verbose'] = False
    server = conf.get('server')
    if not server:
        server_ops = servers.keys()
        server_ops.sort()
        print "Missing --server=name, one of: %s" % ', '.join(server_ops)
        return None, 0
    if conf['reload'] and allow_reload:
        if os.environ.get(reloader_environ_key):
            if conf['verbose']:
                print "Running reloading file monitor"
            reloader.install(conf.get('reload_interval', 1), False)
        else:
            try:
                return restart_with_reloader(conf)
            except KeyboardInterrupt:
                return None, 0
    if conf.get('sys_path'):
        update_sys_path(conf['sys_path'], conf['verbose'])
    app = make_app(conf)
    return conf, app

def run_commandline(args):
    conf, app = load_commandline(args)
    if conf is None:
        return app
    return run_server(conf, app)

def run_server(conf, app):
    server = servers[conf['server']]
    if conf['verbose']:
        print "Starting server."
    try:
        server(conf, app)
    except KeyboardInterrupt:
        # This is an okay error
        pass
    return 0
    

def load_conf(conf, filename, default=False):
    if isinstance(filename, (list, tuple)):
        for fn in filename:
            load_conf(conf, fn, default=default)
        return
    if os.path.exists(filename):
        if conf['verbose']:
            print 'Loading configuration from %s' % filename
        conf.load(filename, default=default)

def update_sys_path(paths, verbose):
    if isinstance(paths, (str, unicode)):
        paths = [paths]
    for path in paths:
        path = os.path.abspath(path)
        if path not in sys.path:
            if verbose:
                print 'Adding %s to path' % path
            sys.path.append(path)
            
def help():
    program = sys.argv[0]
    return help_message % {'program': program}

def twisted_serve(conf, app):
    print 'Twisted support has been temporarily removed from Paste.'

servers['twisted'] = twisted_serve

def scgi_serve(conf, app):
    thirdparty.add_package('scgi')
    from paste.scgiserver import serve_application
    prefix = conf.get('scgi_prefix', '/')
    serve_application(app, prefix, port=int(conf.get('port', 4000)))

servers['scgi'] = scgi_serve

def wsgiutils_serve(conf, app):
    thirdparty.add_package('wsgiutils')
    from wsgiutils import wsgiServer
    server = wsgiServer.WSGIServer(
        (conf.get('host', 'localhost'),
         int(conf.get('port', 8080))), {'': app})
    server.serve_forever()

servers['wsgiutils'] = wsgiutils_serve

def cgi_serve(conf, app):
    replacements = {}
    replacements['default_config_fn'] = os.path.abspath(default_config_fn)

    # Ideally, other_conf should be any options that came from the
    # command-line.
    # @@: This assumes too much about the ordering of namespaces.
    other_conf = dict(conf.namespaces[-2])
    # Not a good idea to let 'verbose' through, but this doesn't really
    # stop any sourced configs from setting it either...
    if other_conf.has_key('verbose'):
        del other_conf['verbose']
    replacements['other_conf'] = other_conf

    template_fn = os.path.join(os.path.dirname(__file__),
                               'server_script_template.py')
    template = open(template_fn).read()
    for name, value in replacements.items():
        template = template.replace('@@' + name + '@@', repr(value))

    print "#!%s" % sys.executable
    print template
    print "if __name__ == '__main__':"
    print "    from paste.cgiserver import run_with_cgi"
    print "    run_with_cgi(app)"

servers['cgi'] = cgi_serve

def console_server(conf, app):
    url = conf.get('url', '/')
    query_string = ''
    if '?' in url:
        url, query_string = url.split('?', 1)
    quiet = conf.get('quiet', False)
    status, headers, content, errors = wsgilib.raw_interactive(
        app, url, QUERY_STRING=query_string)
    any_header = False
    if not quiet or int(status.split()[0]) != 200:
        print 'Status:', status
        any_header = True
    for header, value in headers:
        if quiet and (
            header.lower() in ('content-type', 'content-length')
            or (header.lower() == 'set-cookie'
                and value.startswith('_SID_'))):
            continue
        print '%s: %s' % (header, value)
        any_header = True
    if any_header:
        print
    if conf.get('compact', False):
        # Remove empty lines
        content = '\n'.join([l for l in content.splitlines()
                             if l.strip()])
    print content
    if errors:
        sys.stderr.write('-'*25 + ' Errors ' + '-'*25 + '\n')
        sys.stderr.write(errors + '\n')

servers['console'] = console_server

def make_app(conf):
    if conf.get('publish_dir'):
        app = wsgiwebkit.webkit(conf['publish_dir'], use_lint=conf.get('lint'))
    elif conf.get('publish_app'):
        app = conf['publish_app']
        if isinstance(app, (str, unicode)):
            from paste.util import import_string
            app = import_string.eval_import(app)
    else:
        # @@ ianb 2005-03-23: This should be removed sometime
        if conf.get('webkit_dir'):
            print 'The webkit_dir configuration variable is no longer supported'
            print 'Use publish_dir instead'
        print "You must provide publish_dir or publish_app"
        sys.exit(2)
    return config_middleware(app, conf)

def restart_with_reloader(conf):
    if conf['verbose']:
        print "Restarting process with reloading on"
    while 1:
        args = [sys.executable] + sys.argv
        new_environ = os.environ.copy()
        new_environ[reloader_environ_key] = 'true'
        exit_code = os.spawnve(os.P_WAIT, sys.executable,
                               args, new_environ)
        if exit_code != 3:
            return None, exit_code
        print "Exit code 3; restarting server"

if __name__ == '__main__':
    sys.exit(run_commandline(sys.argv[1:]))
