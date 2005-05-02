import os
from paste import wsgilib

def urlparser_hook(environ):
    if not environ.has_key('console.base_url'):
        environ['console.base_url'] = environ['SCRIPT_NAME']
