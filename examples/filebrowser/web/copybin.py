from filebrowser.sitepage import *
from py.path import local
import py

class copybin(SitePage):

    bins = ['copy', 'cut']

    def setup(self):
        for fn in self.fields.getlist('copy'):
            self.copybin[fn] = 'copy'
        for fn in self.fields.getlist('cut'):
            self.copybin[fn] = 'cut'
        for fn in self.fields.getlist('remove'):
            if fn in self.copybin:
                del self.copybin[fn]
        if self.fields.get('clear'):
            self.copybin.clear()
        if 'paste' in self.fields:
            return self.paste()
        self.update_copybin_display()

    def paste(self):
        if not self.copybin:
            self.message.write('No items to paste')
            self.redirect(self.fields.back)
            return
        dest = self.root.join(self.fields.paste)
        copied = 0
        moved = 0
        for filename, copytype in self.copybin.items():
            path = self.root.join(filename)
            if copytype == 'copy':
                copied += 1
                path.copy(dest)
            elif copytype == 'cut':
                try:
                    path.move(dest)
                except py.error.ENOTEMPTY, e:
                    self.message.write(
                        'Cannot move %s (file by the same name exists' % dest)
                else:
                    moved += 1
        msg = []
        if copied:
            msg.append('%i file%s copied' % (
                copied, copied>1 and 's' or ''))
        if moved:
            msg.append('%i file%s moved' % (
                moved, moved>1 and 's' or ''))
        msg = ', '.join(msg)
        self.copybin.clear()
        self.message.write('%s to %s' % (msg, self.fields.paste))
        self.redirect(self.fields.back)
