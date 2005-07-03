import re
import os
import mimetypes
from paste.wareweb import dispatch, public
from paste.httpexceptions import *
import sitepage

view_servlet_module = None

class BadFilePath(Exception):
    pass

class PathContext(object):

    path_classes = {}

    def __init__(self, root):
        self.root = root

    def path(self, path):
        filename = self.root + '/' + path.lstrip('/')
        if os.path.isdir(filename):
            ptype = 'dir'
        else:
            ptype = os.path.splitext(filename)[1]
        path_class = self.path_classes.get(
            ptype, self.path_classes['*'])
        return path_class(path, filename, self)

    @classmethod
    def register_class(cls, path_class):
        assert not isinstance(path_class.extensions, (str, unicode))
        for ptype in path_class.extensions:
            assert ptype not in cls.path_classes, (
                "When adding class %r, conflict with class %r for "
                "extension %r" % (path_class, cls.path_classes[ptype],
                                  ptype))
            cls.path_classes[ptype] = path_class

class Path(sitepage.SitePage):

    extensions = ['*']

    dispatch = dispatch.ActionDispatch(
        action_name='action',
        default_action='view_raw')

    isdir = False

    def __init__(self, path, filename, context):
        super(Path, self).__init__()
        self.path = path
        self.filename = filename
        self.pathcontext = context
        self.root = context.root
        self.mimetype, self.encoding = mimetypes.guess_type(self.filename)
        if not self.mimetype:
            self.mimetype = 'application/octet-stream'
        self.basename = os.path.basename(filename)
        self.exists = os.path.exists(filename)

    def __str__(self):
        return self.path

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.path)

    def setup(self):
        self.title = 'File: %s' % self.basename
        self.options.parent = {
            'url': self.pathurl.up(),
            'name': self.pathurl.up().name() or 'root',
            }
        self.setup_file()
        
    def setup_file(self):
        mime = self.mimetype
        if mime and mime.startswith('text/'):
            self.options.content = self.read()
        else:
            self.options.content = None
        self.options.is_image = mime and mime.startswith('image/')
        self.options.use_iframe = mime == 'text/html'

    def action_view(self):
        self.view = 'view_file.pt'
        self.options.allow_edit = self.mimetype.startswith('text/')

    def join(self, name):
        parts = name.split('/')
        for part in parts:
            if part.startswith('.'):
                raise BadFilePath(
                    "The path part %r starts with '.', which is illegal"
                    % part)
        if ':' in name:
            raise BadFilePath(
                "The path %r contains ':', which is illegal" % name)
        if '\\' in name:
            raise BadFilePath(
                "The path %r contains '\\', which is illegal" % name)
        name = name.lstrip('/')
        name = re.sub(r'//+', '/', name)
        new_path = self.path + '/' + name
        return self.pathcontext.path(new_path)

    bad_regexes = [
        re.compile(r'<script.*?</script>', re.I+re.S),
        re.compile(r'style="[^"]*position:.*?"', re.I+re.S),
        ]

    def action_view_raw(self):
        self.view = None
        if not self.exists:
            raise HTTPNotFound
        self.set_header('Content-type', self.mimetype)
        content = self.read()
        if (self.mimetype.startswith('text/html')
            and servlet.fields.get('html') == 'clean'):
            for bad_regex in bad_regexes:
                content = self.bad_regex.sub('', content)
        self.write(content)

    def action_edit(self):
        self.view = 'edit_text.pt'
        self.options.content = self.read()
        self.options.action = str(self.pathurl)

    def action_save(self):
        content = self.fields.content
        f = open(self.filename, 'wb')
        f.write(content)
        f.close()
        self.message.write('%i bytes saved' % len(content))
        self.redirect(str(self.pathurl(action='view')))

    def read(self):
        f = open(self.filename, 'rb')
        content = f.read()
        f.close()
        return content
        
PathContext.register_class(Path)

class Dir(Path):

    extensions = ['dir']

    isdir = True

    def setup_file(self):
        files = []
        for filename in sorted(os.listdir(self.filename)):
            try:
                path_servlet = self.join(filename)
            except BadFilePath:
                continue
            files.append({
                'path': path_servlet,
                'name': filename,
                'url': self.pathurl(filename, action='view'),
                'copyid': self.pathid('copy_', str(path_servlet)),
                })
            if path_servlet.isdir:
                files[-1]['name'] += '/'
        self.options.files = files

    def action_view_raw(self):
        self.action_view()

    def action_view(self):
        self.view = 'directory.pt'

PathContext.register_class(Dir)

