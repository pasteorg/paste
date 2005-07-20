from filebrowser.sitepage import *

class addfile_form(SitePage):

    def setup(self):
        root = self.pathcontext.path(self.config.get('blank_file_dir', '/'))
        self.options.blanks = root.find_filename('blank')
        
        
        