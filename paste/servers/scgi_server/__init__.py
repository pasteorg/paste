from paste.util import thirdparty
thirdparty.add_package('scgi')
from scgiserver import serve_application

def serve(conf, app):
    prefix = conf.get('root_url', '').rstrip('/')
    serve_application(app, prefix, port=int(conf.get('port', 4000)))

options = [
    ('port', 'Port to serve on (default 4000).'),
    ('root_url', 'The URL level to expect for incoming connections; if not set and this is not bound to /, then SCRIPT_NAME and PATH_INFO may be incorrect.'),
    ]

description = """\
A pre-forking SCGI server.  SCGI is a FastCGI alternative
(see <http://www.mems-exchange.org/software/scgi/> for more).
"""
