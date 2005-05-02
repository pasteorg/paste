import os
from Component import CPage
from Component.notify import NotifyComponent
from ZPTKit import ZPTComponent
from paste import httpexceptions

class SitePage(CPage):

    components = [
        ZPTComponent([os.path.join(os.path.dirname(__file__),
                                   'templates')]),
        NotifyComponent()]
    
    def title(self):
        return self.options.get('title', CPage.title(self))

    def awake(self, trans):
        CPage.awake(self, trans)
        env = trans.request().environ()
        if env['REMOTE_ADDR'] != '127.0.0.1':
            raise httpexceptions.HTTPForbidden
        if env['wsgi.multiprocess'] or env['wsgi.run_once']:
            raise httpexceptions.HTTPServerError(
                'This application can only be run under single-process '
                '(typically multi-threaded) long-running servers')
        self.baseURL = self.request().environ()['console.base_url']
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
