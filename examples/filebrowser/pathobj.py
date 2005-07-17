import re
import os
import mimetypes
import itertools
import random
import urllib
import cgi
import htmlentitydefs
from paste.wareweb import dispatch, public
from paste.httpexceptions import *
import sitepage

view_servlet_module = None

class BadFilePath(Exception):
    pass

def html_quote(v):
    return cgi.escape(v, 1)
def html_unquote(v, encoding='UTF8'):
    for name, codepoint in htmlentitydefs.name2codepoint.iteritems():
        v = v.replace('&%s;' % name, unichr(codepoint).encode(encoding))
    return v

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
        path_class = self.path_classes.get(ptype)
        if not path_class:
            mimetype, encoding = mimetypes.guess_type(filename)
            if mimetype:
                path_class = self.path_classes.get(mimetype)
            if mimetype and not path_class:
                path_class = self.path_classes.get(mimetype.split('/')[0]+'*')
        if not path_class:
            path_class = self.path_classes['*']
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
    allow_edit = False
    view_file_view = 'view_file.pt'

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
        self.options.allow_edit = self.allow_edit
        self.setup_file()
        
    def setup_file(self):
        mime = self.mimetype
        if mime and mime.startswith('text/'):
            self.options.content = self.read()
        else:
            self.options.content = None
        self.options.use_iframe = mime == 'text/html'

    def action_view(self):
        self.view = self.view_file_view

    def action_download(self):
        # @@: This loads the entire file into memory, but currently
        # Wareweb has no streaming method -- really it should forward
        # the request to a WSGI file-serving application
        self.view = None
        self.set_header('content-type', self.mimetype)
        f = open(self.filename, 'rb')
        self.write(f.read())
        f.close()

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
            and self.fields.get('html') == 'clean'):
            for bad_regex in bad_regexes:
                content = self.bad_regex.sub('', content)
        self.write(content)

    def action_save(self):
        content = self.fields.content
        self.write_text(content)
        self.message.write('%i bytes saved to %s'
                           % (len(content), self.basename))
        self.redirect(str(self.pathurl(action='view')))

    def read(self):
        f = open(self.filename, 'rb')
        content = f.read()
        f.close()
        return content

    def write_text(self, content):
        f = open(self.filename, 'wb')
        f.write(content)
        f.close()
        
PathContext.register_class(Path)

class Image(Path):

    extensions = ['.png', '.gif', '.jpg', 'image/*']
    view_file_view = 'view_image.pt'

PathContext.register_class(Image)

class TextFile(Path):

    extensions = ['.txt', 'text/plain']
    allow_edit = True
    edit_view = 'edit_text.pt'

    def action_view(self):
        if self.fragment:
            # The HTML iframe is nice in a fragment
            self.view = 'view_html.pt'
        else:
            self.view = 'view_text.pt'

    def action_edit(self):
        self.view = self.edit_view
        self.options.content = self.read()
        self.options.action = str(self.pathurl)
        self.options.ta_height = self.cookies.get('default_ta_height', 10)

PathContext.register_class(TextFile)

class HTMLFile(TextFile):

    allow_edit = True
    extensions = ['.html', '.htm', 'text/html']
    edit_view = 'edit_html.pt'

    def action_view(self):
        self.view = 'view_html.pt'

    def action_edit(self):
        super(HTMLFile, self).action_edit()
        content = self.read()
        head, body, tail = self.split_content(content)
        self.options.content = body
        props = self.read_properties(head)
        op_props = self.options.properties = []
        for name, value in sorted(props.items()):
            op_props.append({
                'description': name,
                'input_name': 'property_' + name,
                'type': 'text',
                'value': value})

    def action_save(self):
        # Unlike Path.save, this doesn't save the entire contents
        # of the file
        content = self.fields.content
        props = {}
        for name, value in self.fields.items():
            if name.startswith('property_'):
                props[name[len('property_'):]] = value
        self.save(content, props)
        self.message.write('File %s saved' % self.basename)
        self.redirect(str(self.pathurl(action='view')))

    def save(self, content, props):
        current = self.read()
        head, body, tail = self.split_content(current)
        new_head = self.save_properties(head, props)
        new_content = new_head + content + tail
        self.write_text(new_content)

    def get_regexes(self, name, default=()):
        regex = self.config.get(name)
        if regex is None:
            regex = []
        if not isinstance(regex, (list, tuple)):
            regex = [regex]
        regex = list(regex)
        if default:
            regex.extend(default)
        for i in range(len(regex)):
            if isinstance(regex[i], (str, unicode)):
                regex[i] = re.compile(regex[i], re.I)
        return regex

    def first_match(self, regexes, body):
        for regex in regexes:
            m = regex.search(body)
            if m:
                return m
        return None

    def split_content(self, content):
        body_start_regex = self.get_regexes(
            'body_start_regex', ['<body.*?>'])
        body_end_regex = self.get_regexes(
            'body_end_regex', ['</body>'])
        m = self.first_match(body_start_regex, content)
        if m:
            head = content[:m.end()]
            content = content[m.end():]
        else:
            head = ''
        m = self.first_match(body_end_regex, content)
        if m:
            tail = content[m.start():]
            content = content[:m.start()]
        else:
            tail = ''
        return head, content, tail

    title_re = re.compile('<title>(.*?)</title>', re.I|re.S)
    def read_properties(self, head):
        prop_regex = self.get_regexes(
            'property_regex')
        props = {}
        m = self.title_re.search(head)
        if m:
            props['title'] = m.group(1)
        for regex in prop_regex:
            for match in regex.finditer(head):
                groups = match.groupdict()
                if 'value' in groups:
                    value = groups['value']
                elif 'html_value' in groups:
                    value = html_unquote(groups['html_value'])
                elif 'url_value' in groups:
                    value = urllib.unquote(groups['url_value'])
                props[match.group('name')] = value
        return props

    def save_properties(self, head, props):
        prop_regex = self.get_regexes(
            'property_regex')
        prop_tmpl = self.config['property_template']
        if 'title' in props:
            title_html = '<title>%s</title>' % html_quote(props['title'])
            m = self.title_re.search(head)
            if m:
                head = head[:m.start()] + title_html + head[m.end():]
                del props['title']
            else:
                head = title_html + head
        for name, value in props.items():
            new_prop = prop_tmpl % {
                'name': name,
                'html_value': html_quote(value),
                'url_value': urllib.quote(value),
                'value': value}
            for regex in prop_regex:
                for match in regex.finditer(head):
                    if name != match.group('name'):
                        continue
                    head = (head[:match.start()] + new_prop
                            + head[match.end():])
                    break
                else:
                    head = new_prop + head
        return head
        

PathContext.register_class(HTMLFile)

class Dir(Path):

    extensions = ['dir']

    isdir = True

    upload_id = itertools.count(random.randint(0, 15000))

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
        self.options.upload_id = self.upload_id.next()
        self.options.upload_url = self.globalurl(
            'uploader', upload_id=self.options.upload_id,
            redirect='/')

    def action_view_raw(self):
        self.action_view()

    def action_view(self):
        self.view = 'directory.pt'

PathContext.register_class(Dir)

