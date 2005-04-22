import os
from wsgikit import wsgilib

def urlparser_hook(environ):
    if not environ.has_key('todo.base_url'):
        environ['todo.base_url'] = environ['SCRIPT_NAME']

def not_found_hook(environ, start_response):

    p = environ['wsgikit.urlparser.not_found_parser']
    username, rest = wsgilib.path_info_split(environ.get('PATH_INFO', ''))
    if username is None:
        return p.not_found(environ, start_response)
    environ['todo.username'] = username
    environ['SCRIPT_NAME'] += '/' + username
    environ['PATH_INFO'] = rest
    return p(environ, start_response)
