import os
import urllib
from py.path import local
from paste import wsgilib
from paste import httpexceptions
from paste import urlparser

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
    if environ.get('browser.resolved'):
        return special_dirs['app'](environ, start_response)
    conf = environ['paste.config']
    path_info = environ.get('PATH_INFO', '')
    for special_dir, parser in special_dirs.items():
        if path_info.startswith('/_%s/' % special_dir):
            environ['browser.resolved'] = True
            wsgilib.path_info_pop(environ)
            return parser(environ, start_response)
    environ['browser.filepath'] = urllib.unquote(environ['PATH_INFO'])
    vars = dict(wsgilib.parse_querystring(environ))
    action = (vars.get('action') or ['index'])[0]
    servlet_fn = os.path.join(os.path.dirname(__file__), action + '.py')
    servlet_app = urlparser.make_py(environ, servlet_fn)
    return servlet_app(environ, start_response)

    
