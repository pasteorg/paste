from paste.util import thirdparty
thirdparty.add_package('flup')
from paste import pyconfig
from optparse import Option

def serve(conf, app):
    from flup.server.scgi import WSGIServer
    return serve_server(conf, app, WSGIServer)

def serve_server(conf, app, server_class):
    root_url = conf.get('root_url', '').rstrip('/')
    server = server_class(
        app,
        bindAddress=(conf.get('host', 'localhost'),
                     int(conf.get('port', '4000'))),
        scriptName=root_url,
        allowedServers=pyconfig.make_list(conf.get('allowed_servers', None)))
    return server.run()

options = [
    Option('--host',
           metavar='HOST',
           help='The host name to bind to (default localhost).  Note, if binding to localhost, only local connections will be allowed.'),
    Option('--port',
           metavar="PORT",
           help='The port to bind to (default 4000).'),
    Option('--root-url',
           metavar="URL",
           help='The URL level to expect for incoming connections; if not set and this is not bound to /, then SCRIPT_NAME and PATH_INFO may be incorrect.'),
    Option('--allowed-servers',
           metavar="URL_LIST",
           help='A list of servers to allow connections from.'),
    ]

description = """\
A SCGI multithreaded server.  SCGI is a FastCGI alternative (see
<http://www.mems-exchange.org/software/scgi/> for more).  This server
is from flup: <http://www.saddi.com/software/flup/>.
"""

# @@: TODO: handle the logging level, or integrate logging
