from $app_name.sitepage import SitePage

class index(SitePage):

    def setup(self):
        self.options.vars = self.request().environ().items()
        self.options.vars.sort()
        self.options.title = 'Welcome to your new app'
        
