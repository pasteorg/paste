from todo_sql.sitepage import SitePage
from todo_sql.db import *

class index(SitePage):

    def setup(self):
        self.options.title = 'List of Lists'
