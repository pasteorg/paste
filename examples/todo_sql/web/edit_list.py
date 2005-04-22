from todo_sql.sitepage import SitePage
from todo_sql.db import *

class edit_list(SitePage):

    def setup(self):
        self.list_id = self.request().field('id')
        if self.list_id != 'new':
            self.list = TodoList.get(int(self.list_id))
        self.options.title = 'Edit list '

    def actions(self):
        return ['save', 'destroy']

    def save(self):
        desc = self.request().field('description')
        if self.list_id == 'new':
            self.list = TodoList(description=desc)
            self.message('List created')
        else:
            self.list.description = desc
            self.message('List updated')
        self.sendRedirectAndEnd('./view_list?id=%s' % self.list.id)

    def destroy(self):
        desc = self.list.description
        self.list.destroySelf()
        self.message('List %s deleted' % desc)
        self.sendRedirectAndEnd('./')
