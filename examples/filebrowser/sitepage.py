import cgi
import itertools
import os
import urllib
from paste.wareweb import *
from paste import wsgilib
from ZPTKit.zptwareweb import ZPTComponent
from py.path import local
import handlers

class SitePage(Servlet):

    message = Notify()
    template = ZPTComponent()
    app_name = 'filebrowser'

    def awake(self):
        super(SitePage, self).awake(call_setup=False)
        self.root = local(self.config['browse_path'])
        if 'browser.filepath' in self.environ:
            self.pathinfo = self.environ['browser.filepath']
            self.path = self.root.join(self.pathinfo)
        else:
            self.pathinfo = ''
            self.path = None
        self.pathurl = URL(self.environ,
                           script_name=self.app_url,
                           path_info=self.pathinfo)
        self.globalurl = URL(self.environ,
                             script_name=self.app_url + '/_app',
                             path_info='')
        self.icons = Icon(self.app_url + '/_icons')
        self.app_static_url = self.app_url + '/_static'
        self.fragment = '_' in self.fields
        self.copybin = self.session.setdefault('copybin', {})
        self.update_copybin_display()
        self.setup()

    def rootedpath(self, path):
        path = str(path)
        assert path.startswith(str(self.root)), (
            "Bad path: %r (doesn't start with %r)" % (path, self.root))
        return path[len(str(self.root)):]

    def handler(self, path=None):
        path = path or self.file
        handler = handlers.get_handler(path)

    def update_copybin_display(self):
        files = self.options.copyfiles = []
        for filename, cutcopy in self.copybin.items():
            path = local(self.root).join(filename)
            files.append(
                {'filename': filename,
                 'url': self.app_url + filename,
                 'path': path,
                 'name': path.basename,
                 'cut': cutcopy=='cut',
                 'copy': cutcopy=='copy',
                 'id': self.pathid('copy_', filename),
                 })
        files.sort(key=lambda x: x['filename'])

    def pathid(self, prefix, path):
        if isinstance(path, local):
            path = self.rootedpath(path)
        return prefix + path.replace('/', '__')

    def copybutton(self, path, copytype='copy'):
        assert copytype in ('copy', 'cut')
        copyurl = self.globalurl('copybin', **{
            copytype: self.rootedpath(path)})
        remote = copyurl.remote(
            id='copybin',
            onComplete='function (req) {new Effect.Highlight(%r)}'
            % self.pathid('copy_', path))
        img = self.icons('edit%s.png' % copytype, alt=copytype,
                         title=copytype)
        return remote.link(img)

    def pastebutton(self, path):
        copyurl = self.globalurl('copybin', paste=self.rootedpath(path),
                                 back=wsgilib.construct_url(self.environ))
        return '<a href="%s">%s</a>' % (
            copyurl, self.icons('editpaste', alt="paste",
                                title="Paste Files"))
    

class URL(object):

    def __init__(self, environ, script_name=None, path_info=None,
                 vars=None):
        if script_name is None:
            script_name = environ['SCRIPT_NAME']
        self.script_name = script_name
        if path_info is None:
            path_info = environ['PATH_INFO']
        self.path_info = path_info
        self.environ = environ
        self.vars = vars or {}
        
    def __str__(self):
        return wsgilib.construct_url(
            self.environ, with_query_string=True, with_path_info=True,
            script_name=self.script_name, path_info=self.path_info,
            querystring=urllib.urlencode(self.vars))

    def __repr__(self):
        return '<URL %s>' % self

    def url_without_qs(self):
        return wsgilib.construct_url(
            self.environ, with_query_string=True, with_path_info=True,
            script_name=self.script_name, path_info=self.path_info,
            querystring='')
    url_without_qs = property(url_without_qs)

    def __getitem__(self, add):
        vars = self.vars.copy()
        path_info = self.path_info
        if add and '=' in add:
            name, value = add.split('=', 1)
            vars[name] = value
        elif add:
            if not path_info.endswith('/'):
                path_info += '/'
            path_info += add
        return self.__class__(self.environ, script_name=self.script_name,
                              path_info=path_info, vars=vars)

    def __call__(self, *args, **kw):
        obj = self[None]
        for arg in args:
            obj = obj[arg]
        for name, value in kw.items():
            obj.vars[name] = value
        return obj

    def remote(self, id=None, **options):
        if id is None:
            id = idgen()
        return JSRemote(self, id, options)

    def toggle(self, id=None, **options):
        if id is None:
            id = idgen()
        return JSToggle(self, id, options)

    def up(self):
        path_info = '/'.join(self.path_info.split('/')[:-1])
        return self.__class__(
            self.environ, script_name=self.script_name,
            path_info=path_info, vars=self.vars)

    def name(self):
        return self.path_info.split('/')[-1]

_idgen_count = itertools.count()
def idgen():
    return 'node%s' % hex(_idgen_count.next() % 0xffffff)[2:]
        
class JSRemote(object):

    def __init__(self, url, id, options):
        self.url = url
        self.id = id
        self.options = options

    def option_js(self, **base):
        base.update(self.options)
        return '{%s}' % (', '.join([
            '%s: %s' % (name, value)
            for name, value in base.items()]))

    def javascript(self):
        return "new Ajax.Updater(%r, %r, %s); return false" % (
            self.id, self.url.url_without_qs,
            self.option_js(parameters=repr(urllib.urlencode(self.url.vars.items())),
                           method=repr('get')))

    javascript = property(javascript)

    def link(self, description, structure=True, **kw):
        if not structure:
            description = cgi.escape(description, 1)
        return '<a href="%s" onclick="%s"%s>%s</a>' % (
            cgi.escape(str(self.url), 1), cgi.escape(self.javascript, 1),
            html_attrs(kw), description)

class JSToggle(JSRemote):

    def javascript(self):
        return "lazyToggle(%r, %r, {link: this, parameters: %r}); return false" % (
            self.id, self.url.url_without_qs,
            self.option_js(parameters=repr(urllib.urlencode(self.url.vars.items())),
                           link='this'))

    javascript = property(javascript)

def html_attrs(kw):
    if not kw:
        return ''
    return ''.join([
        ' %s="%s"' % (name, cgi.escape(str(value), 1))
        for name, value in kw.items()])

class Icon(object):

    def __init__(self, url, attrs=None):
        self.url = url
        self.attrs = attrs or {}

    def html__get(self):
        return '<img src="%s" border=0%s>' % (
            self.url, html_attrs(self.attrs))
    html = property(html__get)

    __str__ = html__get

    def copy(self):
        return self.__class__(self.url, self.attrs.copy())

    def __call__(self, *names, **kw):
        obj = self.copy()
        for name in names:
            obj = obj[name]
        obj.attrs.update(kw)
        return obj

    def __getitem__(self, icon_name):
        if '=' in icon_name:
            obj = self.copy()
            name, value = icon_name.split('=', 1)
            value = value.replace('+', ' ')
            obj.attrs[name] = value
            return obj
        else:
            return self.__class__(self.url + '/' + icon_name)

# This protects "from sitepage import *", since we will no longer
# need these variables:
del ZPTComponent
del Notify
