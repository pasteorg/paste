import mimetypes
import re
from filebrowser.sitepage import SitePage

bad_regexes = [
    re.compile(r'<script.*?</script>', re.I+re.S),
    re.compile(r'style="[^"]*position:.*?"', re.I+re.S),
    ]

class download(SitePage):

    def setup(self):
        mime, _ = mimetypes.guess_type(str(self.path))
        self.set_header('Content-type', mime)
        self.view = None
        content = self.path.read()
        if self.fields.get('html') == 'clean':
            for bad_regex in bad_regexes:
                content = bad_regex.sub('', content)
        self.write(content)
