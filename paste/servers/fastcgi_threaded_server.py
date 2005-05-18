import os
from optparse import Option
from paste.util import thirdparty
thirdparty.add_package('flup')
from paste import pyconfig

def serve(conf, app):
    from flup.server.fcgi import WSGIServer
    return serve_server(conf, app, WSGIServer)

def serve_server(conf, app, server_class):
    if conf.get('host'):
        if not conf.get('port'):
            raise ValueError(
                "There is no default port for FastCGI; if you give 'host' you must provide 'port'")
        address = (conf['host'], conf['port'])
    elif conf.get('socket'):
        address = conf['socket']
    else:
        address = os.path.join(conf.get('root_path', ''), 'fcgi_sock')
    # @@: Right now there's no automatic socket, and the parent server
    # can't start up this server in any way.
    server = server_class(
        app,
        bindAddress=address,
        multiplexed=pyconfig.make_bool(conf.get('multiplexed', False)))
    return server.run()

options = [
    Option('--socket',
           metavar="FILENAME",
           help='The filename of a socket to listen to for connections.  Default is fcgi_sock in the current directory.'),
    Option('--host',
           metavar="HOST",
           help='The host to bind to when listening for connections over the network.  You must also provide port if you provide host.'),
    Option('--port',
           metavar="PORT",
           help='The port to bind to.'),
    Option('--multiplex',
           metavar="true/false",
           help='Option to multiplex connections (default: false).'),
    ]

description = """\
A FastCGI threaded server.  For more information on FastCGI see
<http://www.fastcgi.com>.  This server is from flup:
<http://www.saddi.com/software/flup/>.
"""
