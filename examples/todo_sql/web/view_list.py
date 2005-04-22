from todo_sql.sitepage import SitePage
from todo_sql.db import *

class view_list(SitePage):

    def setup(self):
        self.options.list = TodoList.get(int(self.request().field('id')))
        self.options.list_items = list(self.options.list.items)
        self.options.title = 'List: %s' % self.options.list.description

    def actions(self):
        return ['check', 'add', 'destroy']

    def check(self):
        field = self.request().field
        for item in self.options.list.items:
            checked = field('item_%s' % item.id, False)
            if not checked and item.done:
                self.message('Item %s marked not done'
                             % item.description)
                item.done = False
            if checked and not item.done:
                self.message('Item %s marked done'
                             % item.description)
                item.done = True
        self.sendRedirectAndEnd(
            './view_list?id=%s' % self.options.list.id)
    
    def add(self):
        desc = self.request().field('description')
        if not desc:
            self.message('You must give a description')
        else:
            TodoItem(todo_list=self.options.list,
                     description=desc)
            self.message('Item added')
        self.sendRedirectAndEnd(
            './view_list?id=%s' % self.options.list.id)

    def destroy(self):
        id = int(self.request.field('item_id'))
        item = TodoItem.get(id)
        assert item.todo_list.id == self.options.list.id
        desc = description
        item.destroySelf()
        self.message("Item %s removed" % desc)
        self.sendRedirectAndEnd(
            './view_list?id=%s' % self.options.list.id)
