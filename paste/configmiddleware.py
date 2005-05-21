from paste import CONFIG
from paste import wsgilib
from paste.docsupport import metadata

__all__ = ['ConfigMiddleware']

class ConfigMiddleware(object):

    """
    A WSGI middleware that adds a ``paste.config`` key to the request
    environment, as well as registering the configuration temporarily
    (for the length of the request) with ``paste.CONFIG``.
    """

    _wsgi_add1 = metadata.WSGIKey('paste.config',
                                  interface='paste.pyconfig.Config')

    def __init__(self, application, config):
        """
        This delegates all requests to `application`, adding a *copy*
        of the configuration `config`.
        """
        self.application = application
        self.config = config

    def __call__(self, environ, start_response):
        conf = environ['paste.config'] = self.config.copy()
        app_iter = None
        CONFIG.push_thread_config(conf)
        try:
            app_iter = self.application(environ, start_response)
        finally:
            if app_iter is None:
                # An error occurred...
                CONFIG.pop_thread_config(conf)
        if type(app_iter) in (list, tuple):
            # Because it is a concrete iterator (not a generator) we
            # know the configuration for this thread is no longer
            # needed:
            CONFIG.pop_thread_config(conf)
            return app_iter
        else:
            def close_config():
                CONFIG.pop_thread_config(conf)
            new_app_iter = wsgilib.add_close(app_iter, close_config)
            return new_app_iter
