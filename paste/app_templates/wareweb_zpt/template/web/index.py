from $app_name.sitepage import SitePage

class index(SitePage):

    def setup(self):
        self.options.vars = self.environ.items()
        self.options.vars.sort()
        self.title = 'Welcome to your new app'

