import sys
import os
from paste import makeapp
from paste import urlparser
from paste import session
from paste import recursive
from paste import httpexceptions

def build_application(conf):
    if not 'publish_dir' in conf:
        print 'You must provide a publish_dir configuration value'
        sys.exit(2)
    directory = conf['publish_dir']
    install_fake_webware = conf.get('install_fake_webware', True)
    if install_fake_webware:
        _install_fake_webware()
    app = urlparser.URLParser(directory, os.path.basename(directory))
    app = makeapp.apply_conf_middleware(
        app, conf,
        [httpexceptions.middleware, session.SessionMiddleware,
         recursive.RecursiveMiddleware])
    app = makeapp.apply_default_middleware(app, conf)
    return app

def install_fake_webware():
    fake_webware_dir = os.path.join(os.path.dirname(__file__),
                                    'FakeWebware')
    if fake_webware_dir in sys.path:
        return
    sys.path.insert(0, fake_webware_dir)
_install_fake_webware = install_fake_webware
