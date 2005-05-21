"""
Helper functions for framework build_application functions.
"""

from paste.util import import_string
from paste import lint
from paste import errormiddleware
from paste import configmiddleware

def apply_conf_middleware(app, conf, first_middleware=()):
    """
    Applies any middleware that the configuration specifies,
    returning the wrapped configuration.

    If first_middleware is given, this middleware is applied most
    closely to the application (before configuration middleware).
    """
    all_middleware = list(first_middleware)
    all_middleware.extend(conf.get('middleware', []))
    for middleware in all_middleware:
        # @@: Should this use plugins too?
        if isinstance(middleware, (str, unicode)):
            middleware = import_string.eval_import(middleware)
        app = middleware(app)
        if conf.get('lint', False):
            app = lint.middleware(app)
    return app

def apply_default_middleware(app, conf):
    """
    Applies middleware that is generally always used.
    """
    app = errormiddleware.ErrorMiddleware(app)
    if conf.get('lint', False):
        app = lint.middleware(app)
    app = configmiddleware.ConfigMiddleware(app, conf)
    return app
