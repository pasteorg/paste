from scgi_threaded_server import *

def serve(conf, app):
    from flup.server.scgi_fork import WSGIServer
    return serve_server(conf, app, WSGIServer)

description = """\
A SCGI forking (multiprocess) server.  SCGI is a FastCGI alternative
(see <http://www.mems-exchange.org/software/scgi/> for more).  This
server (unlike the 'scgi' server, which is also forking) is from flup:
<http://www.saddi.com/software/flup/>.
"""
