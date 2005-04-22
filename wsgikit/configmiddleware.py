def config_middleware(app, config):

    def replacement_app(environ, start_response):
        environ['paste.config'] = config.copy()
        return app(environ, start_response)

    return replacement_app
