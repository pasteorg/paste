"""
wkserver constructs the WSGI stack of middleware to serve WebKit
content.  It actually does not include a server (umm... bad name;
"application" was taken).

Use ``some_server(webkit('/path/to/servlets/'))``
"""

import sys
import os
from paste import urlparser
from paste import session
from paste import recursive
from paste import httpexceptions
from paste import lint
from paste import error_middleware

def webkit(directory, install_fake_webware=True, use_lint=False):
    if install_fake_webware:
        _install_fake_webware()
    app = urlparser.URLParser(directory, os.path.basename(directory))
    if use_lint:
        app = lint.middleware(app)
    app = httpexceptions.middleware(app)
    if use_lint:
        app = lint.middleware(app)
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

if __name__ == '__main__':
    if os.environ.has_key('SERVER_NAME'):
        import cgiserver
        cgiserver.run_with_cgi(webkit(os.path.dirname(__file__)),
                               use_cgitb=True,
                               redirect_stdout=True)
    else:
        import wsgilib
        import sys
        import os
        if '-h' in sys.argv or '--help' in sys.argv or not sys.argv[1:]:
            print 'Usage: %s URL_PATH' % sys.argv[0]
            print 'Run like: CLIENT_DIR=XXX %s URL_PATH' % sys.argv[0]
            print 'to put the root of the URL_PATH in in XXX'
            sys.exit()
        root = os.environ.get('CLIENT_DIR', os.path.dirname(__file__))
        application = webkit(root)
        def prapp(url, app=None):
            if app is None:
                app = application
            print wsgilib.interactive(app, url)
        prapp(sys.argv[1])
