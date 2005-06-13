import mimetypes
from filebrowser.sitepage import SitePage

class index(SitePage):

    def setup(self):
        self.title = 'File: %s' % self.path.basename
        self.options.parent = {
            'url': self.pathurl.up(),
            'name': self.pathurl.up().name() or 'root',
            }
        if self.path.check(dir=1):
            self.setup_dir()
        else:
            self.setup_file()

    def setup_dir(self):
        files = []
        for f in self.path.listdir(sort=True):
            files.append({
                'path': f,
                'name': f.basename,
                'url': self.pathurl[f.basename],
                'copyid': self.pathid('copy_', f),
                })
            if f.check(dir=1):
                files[-1]['name'] += '/'
        self.options.files = files
        self.view = 'directory.pt'
        
    def setup_file(self):
        self.options.mimetype, _ = mimetypes.guess_type(str(self.path))
        mime = self.options.mimetype
        self.view = 'view_file.pt'
        if mime and mime.startswith('text/'):
            self.options.content = self.path.read()
        else:
            self.options.content = None
        self.options.is_image = mime and mime.startswith('image/')
        self.options.use_iframe = mime == 'text/html'
