from paste.util import thirdparty
thirdparty.add_package('scgi')
from scgiserver import serve_application

def serve(conf, app):
    prefix = conf.get('scgi_prefix', '/')
    serve_application(app, prefix, port=int(conf.get('port', 4000)))
