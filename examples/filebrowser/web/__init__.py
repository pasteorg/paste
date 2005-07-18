import os
import urllib
from paste import CONFIG
from paste import wsgilib
from paste import httpexceptions
from paste import urlparser
from filebrowser import pathobj

def urlparser_hook(environ):
    if not environ.has_key('filebrowser.base_url'):
        environ['filebrowser.base_url'] = environ['SCRIPT_NAME']

special_dirs = {}

for special_dir in ['js-lib', 'icons', 'static']:
    special_dirs[special_dir] = urlparser.URLParser(
        os.path.join(os.path.dirname(os.path.dirname(__file__)),
                     special_dir), None)

special_dirs['app'] = urlparser.URLParser(
    os.path.dirname(__file__), 'filebrowser.web')

def application(environ, start_response):
    context = environ['filebrowser.pathcontext'] = pathobj.PathContext(
        root=environ['paste.config']['browse_path'])
    if environ.get('filebrowser.resolved'):
        return special_dirs['app'](environ, start_response)
    path_info = environ.get('PATH_INFO', '')
    for special_dir, parser in special_dirs.items():
        if path_info.startswith('/_%s/' % special_dir):
            environ['filebrowser.resolved'] = True
            wsgilib.path_info_pop(environ)
            return parser(environ, start_response)
    path = urllib.unquote(environ['PATH_INFO'])
    path_servlet = context.path(path)
    return path_servlet(environ, start_response)

    
