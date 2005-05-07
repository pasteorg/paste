import os
from paste import wsgilib
from paste import wdg_validate

def urlparser_hook(environ):
    if not environ.has_key('console.base_url'):
        environ['console.base_url'] = environ['SCRIPT_NAME']

def urlparser_wrap(environ, start_response, app):
    return wdg_validate.WDGValidateMiddleware(app)(
        environ, start_response)
