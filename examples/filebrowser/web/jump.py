from filebrowser.sitepage import *

class jump(SitePage):

    def setup(self):
        name = self.fields.name.strip()
        action = 'view'
        if name.startswith('edit:'):
            action = 'edit'
            name = name[5:].strip()
        root = self.pathcontext.path('/')
        if name == 'root':
            possible = [root]
        else:
            possible = root.find_filename(name)
        if not possible:
            self.message.write('No files with %r found' % name)
            self.redirect(self.environ['HTTP_REFERER'])
        dest = possible[0]
        if possible[1:]:
            self.message.write('Other matches:')
            for path in possible[1:]:
                self.message.write(
                    '<a href="%s">%s</a>'
                    % (self.pathurl(path.path, action=action), path.path))
        self.redirect(self.pathurl(dest.path, action=action))
        
                