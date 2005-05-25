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

from paste import reloader
from paste import CONFIG
from paste.util import plugin
from paste import pyconfig

reloader_environ_key = 'WSGI_RELOADER_SHOULD_RUN'

default_config_fn = os.path.join(os.path.dirname(__file__),
                                 'default_config.conf')

def load_commandline(args, allow_reload=True):
    conf = pyconfig.Config(with_default=True)
    conf.load_commandline(
        args, bool_options=['help', 'verbose', 'reload', 'debug', 'quiet',
                            'no_verbose', 'list_servers', 'daemon'],
        aliases={'h': 'help', 'v': 'verbose', 'f': 'config_file',
                 'D': 'debug', 'q': 'quiet'})
    if conf.get('no_verbose'):
        conf['verbose'] = False
    if not conf.get('no_server_conf') and os.path.exists('server.conf'):
        load_conf(conf, 'server.conf', True)
    if conf.get('config_file'):
        load_conf(conf, conf['config_file'], True)
    if conf['quiet']:
        conf['verbose'] = False
    if conf.get('help'):
        return conf, 'help'
    if conf.get('list_servers'):
        return conf, None
    server = conf.get('server')
    if not server:
        server_ops = plugin.find_plugins('servers', '_server')
        server_ops.sort()
        print "Missing --server=NAME"
        print "Use --list-servers for a description of available servers"
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
    conf.update_sys_path()
    app = make_app(conf)
    return conf, app

def load_commandline_options():
    """
    Fake command line options, for use with help messages
    """
    from optparse import Option, OptionGroup
    return [
        Option('-v', '--verbose',
               help="Be verbose",
               action="store_true"),
        Option('--reload',
               help="Activate reloader",
               action="store_true"),
        Option('-D', '--debug',
               help="Turn on debug mode (tracebacks display in browser)",
               action="store_true"),
        Option('-q', '--quiet',
               help="Display as little output as possible",
               action="store_true"),
        Option('-f', '--config-file',
               help="Load the given configuration file (default: server.conf)",
               metavar="FILENAME"),
        Option('--no-verbose',
               help="Suppress verbose (useful if configuration specifies verbose)",
               action="store_true"),
        Option('--list-servers',
               help="List available servers",
               action="store_true"),
        ]
        

def run_commandline(args):
    conf, app = load_commandline(args)
    if conf is None:
        return app
    CONFIG.push_process_config(conf)
    return run_server(conf, app)

def get_server_mod(server_name):
    try:
        server_mod = plugin.load_plugin_module(
            dir='servers',
            dir_package='paste.servers',
            name=server_name,
            name_extension='_server')
    except plugin.PluginNotFound, e:
        print "Error loading server: %s" % e
        print "Available servers:"
        server_ops = plugin.find_plugins('servers', '_server')
        server_ops.sort()
        print ', '.join(server_ops)
        sys.exit(1)
    return server_mod

def run_server(conf, app):
    server_mod = get_server_mod(conf['server'])
    if conf['verbose']:
        print "Starting server."
    try:
        server_mod.serve(conf, app)
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
            
def help():
    program = sys.argv[0]
    return help_message % {'program': program}

def make_app(conf):
    framework_name = conf.get('framework', 'default')
    framework = plugin.load_plugin_module(
        os.path.join(os.path.dirname(__file__), 'frameworks'),
        'paste.frameworks',
        framework_name,
        '_framework')
    app = framework.build_application(conf)
    return app

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
        if conf['verbose']:
            print '-'*20, 'Restarting', '-'*20

if __name__ == '__main__':
    sys.exit(run_commandline(sys.argv[1:]))
