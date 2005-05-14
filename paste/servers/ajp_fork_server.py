from ajp_threaded_server import *

def serve(conf, app):
    from flup.server.ajp_fork import WSGIServer
    return serve_server(conf, app, WSGIServer)

description = """\
An AJP (Apache Jarkarta Tomcat Connector) forking (multiprocess)
server.  For more about AJP see
<http://jakarta.apache.org/tomcat/connectors-doc/>.  This server is
from flup <http://www.saddi.com/software/flup/>
"""
