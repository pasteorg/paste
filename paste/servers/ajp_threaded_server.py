from paste.util import thirdparty
thirdparty.add_package('flup')
from paste import pyconfig

def serve(conf, app):
    from flup.server.ajp import WSGIServer
    return serve_server(conf, app, WSGIServer)

def serve_server(conf, app, server_class):
    root_url = conf.get('root_url', '').rstrip('/')
    server = server_class(
        app,
        scriptName=root_url,
        bindAddress=(conf.get('host', 'localhost'),
                     int(conf.get('port', 8009))),
        allowedServers=pyconfig.make_list(conf.get('allowed_servers', None)))
    return server.run()

options = [
    ('host', 'The host name to bind to (default localhost).  Note, if binding to localhost, only local connections will be allowed.'),
    ('port', 'The port to bind to (default 8009).'),
    ('root_url', 'The URL level to expect for incoming connections; if not set and this is not bound to /, then SCRIPT_NAME and PATH_INFO may be incorrect.'),
    ('allowed_servers', 'A list of servers to allow connections from.'),
    ]

description = """\
An AJP (Apache Jarkarta Tomcat Connector) threaded server.  For more
about AJP see <http://jakarta.apache.org/tomcat/connectors-doc/>.
This server is from flup: <http://www.saddi.com/software/flup/>.
"""

help = """\
When configuring, you would set worker.properties to something like
(for mod_jk):

  worker.list=foo
  worker.foo.port=8009
  worker.foo.host=localhost
  worker.foo.type=ajp13

Example httpd.conf (for mod_jk):

  JkWorkersFile /path/to/workers.properties
  JkMount /* foo

If your ajp application is not on the root, you SHOULD specify
root_url so that SCRIPT_NAME and PATH_INFO are correct.
"""

# @@: TODO: handle the logging level, or integrate logging
