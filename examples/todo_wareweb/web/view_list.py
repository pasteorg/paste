from todo_wareweb.sitepage import SitePage
from todo_wareweb.db import *
from paste.wareweb import ActionDispatch, public

class view_list(SitePage):

    dispatch = ActionDispatch()

    def setup(self):
        self.options.list = TodoList.get(int(self.fields.id))
        self.options.list_items = list(self.options.list.items)
        self.options.title = 'List: %s' % self.options.list.description

    @public
    def check(self):
        for item in self.options.list.items:
            checked = self.fields.get('item_%s' % item.id, False)
            if not checked and item.done:
                self.message.write('Item %s marked not done'
                                   % item.description)
                item.done = False
            if checked and not item.done:
                self.message.write('Item %s marked done'
                                   % item.description)
                item.done = True
        self.redirect('view_list', id=self.options.list.id)

    @public
    def add(self):
        desc = self.fields.description
        if not desc:
            self.message.write('You must give a description')
        else:
            TodoItem(todo_list=self.options.list,
                     description=desc)
            self.message.write('Item added')
        self.redirect(
            'view_list', id=self.options.list.id)

    @public
    def destroy(self):
        id = int(self.fields.item_id)
        item = TodoItem.get(id)
        assert item.todo_list.id == self.options.list.id, (
            "You are trying to delete %s, which does not "
            "belong to the list %s" % (item, self.options.list))
        desc = item.description
        item.destroySelf()
        self.message.write("Item %s removed" % desc)
        self.redirect('view_list', id=self.options.list.id)
        
