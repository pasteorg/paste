from console.sitepage import SitePage
from console.JSONComponent import JSONComponent

global_namespace = {}

class index(SitePage):

    components = SitePage.components + [
        JSONComponent(baseConfig='console')]

    def setup(self):
        self.options.title = 'Console'
        
    def jsonMethods(self):
        return ['run']
    
    def run(self):
        return 'Cool dude!'
