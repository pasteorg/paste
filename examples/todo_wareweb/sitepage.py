from paste.wareweb import Servlet, Notify
from ZPTKit.zptwareweb import ZPTComponent

class SitePage(Servlet):

    zpt = ZPTComponent()
    message = Notify()

    def awake(self):
        self.app_static_url = self.app_url + '/static'
        super(SitePage, self).awake()
    
    def title__get(self):
        return self.options.get('title', super(SitePage, self).title)
