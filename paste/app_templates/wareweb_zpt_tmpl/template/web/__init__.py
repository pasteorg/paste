import os
from paste import wsgilib

def urlparser_hook(environ):
    if not environ.has_key('${app_name}.base_url'):
        environ['${app_name}.base_url'] = environ['SCRIPT_NAME']
