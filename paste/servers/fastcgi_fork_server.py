from fastcgi_threaded_server import *

def serve(conf, app):
    from flup.server.fcgi_fork import WSGIServer
    return serve_server(conf, app, WSGIServer)

description = """\
A FastCGI forking (multiprocess) server.  For more information on
FastCGI see <http://www.fastcgi.com>.  This server is from flup:
<http://www.saddi.com/software/flup/>.
"""
