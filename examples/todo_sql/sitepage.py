import os
from Component import CPage
from Component.notify import NotifyComponent
from ZPTKit import ZPTComponent
from todo_sql.db import *

class SitePage(CPage):

    components = [
        ZPTComponent([os.path.join(os.path.dirname(__file__),
                                   'templates')],
                     use_error_formatter=False),
        NotifyComponent()]
    
    def title(self):
        return self.options.get('title', CPage.title(self))

    def awake(self, trans):
        CPage.awake(self, trans)
        self.baseURL = self.request().environ()['todo_sql.base_url']
        self.baseStaticURL = self.baseURL + '/static'
        self.options.lists = list(TodoList.select())
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
