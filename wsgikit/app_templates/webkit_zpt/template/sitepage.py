import os
from Component import CPage
from Component.notify import NotifyComponent
from ZPTKit import ZPTComponent

class SitePage(CPage):

    components = [
        ZPTComponent([os.path.join(os.path.dirname(__file__),
                                   'templates')]),
        NotifyComponent()]
    
    def title(self):
        return self.options.get('title', CPage.title(self))

    def awake(self, trans):
        CPage.awake(self, trans)
        self.baseURL = self.request().environ()['$app_name.base_url']
        self.baseStaticURL = self.baseURL + '/static'
        self.setup()

    def setup(self):
        pass

    def sleep(self, trans):
        self.teardown()
        CPage.sleep(self, trans)

    def teardown(self):
        pass

    def writeHTML(self):
        self.writeTemplate()
