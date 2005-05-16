import sys
import os
from paste import urlparser
from paste import session
from paste import recursive
from paste import httpexceptions
from paste import lint
from paste import error_middleware

def build_application(conf):
    if not 'publish_dir' in conf:
        print 'You must provide a publish_dir configuration value'
        sys.exit(2)
    directory = conf['publish_dir']
    install_fake_webware = conf.get('install_fake_webware', True)
    use_lint = conf.get('lint', False)
    if install_fake_webware:
        _install_fake_webware()
    app = urlparser.URLParser(directory, os.path.basename(directory))
    if use_lint:
        app = lint.middleware(app)
    app = httpexceptions.middleware(app)
    if use_lint:
        app = lint.middleware(app)
    print session
    app = session.SessionMiddleware(app)
    if use_lint:
        app = lint.middleware(app)
    app = recursive.RecursiveMiddleware(app)
    if use_lint:
        app = lint.middleware(app)
    app = error_middleware.ErrorMiddleware(app)
    # I'll skip the use of lint on recursive, because it doesn't modify
    # its output much at all
    return app

def install_fake_webware():
    fake_webware_dir = os.path.join(os.path.dirname(__file__),
                                    'FakeWebware')
    if fake_webware_dir in sys.path:
        return
    sys.path.insert(0, fake_webware_dir)
_install_fake_webware = install_fake_webware
