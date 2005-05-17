from paste import CONFIG
from paste import wsgilib

def config_middleware(app, config):

    def replacement_app(environ, start_response):
        conf = environ['paste.config'] = config.copy()
        app_iter = None
        CONFIG.push_thread_config(conf)
        try:
            app_iter = app(environ, start_response)
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

    return replacement_app
