from todo_wareweb.sitepage import SitePage
from todo_wareweb.db import *

class index(SitePage):

    def setup(self):
        self.options.title = 'List of Lists'
        self.options.lists = list(TodoList.select())
        
