import shutil
from filebrowser.sitepage import *

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
        dest = self.pathcontext.path(self.fields.paste)
        copied = 0
        moved = 0
        for filename, copytype in self.copybin.items():
            path = self.pathcontext.path(filename)
            dest_path = dest.join(path.basename)
            if copytype == 'copy':
                copied += 1
                shutil.copyfile(path.filename, dest_path.filename)
            elif copytype == 'cut':
                try:
                    shutil.movefile(path.filename, dest_path.filename)
                except Exception, e:
                    self.message.write(
                        'Cannot move to %s (%s)' % (dest, e))
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
