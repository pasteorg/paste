from todo_wareweb.sitepage import SitePage
from todo_wareweb.db import *
from paste.wareweb import ActionDispatch, public

class edit_list(SitePage):

    dispatch = ActionDispatch()

    def setup(self):
        self.list_id = self.fields.id
        if self.list_id != 'new':
            self.list = TodoList.get(int(self.list_id))
        self.options.title = 'Edit list '

    @public
    def save(self):
        desc = self.fields.description
        if self.list_id == 'new':
            self.list = TodoList(description=desc)
            self.message.write('List created')
        else:
            self.list.description = desc
            self.message.write('List updated')
        self.redirect('view_list', id=self.list.id)

    @public
    def destroy(self):
        desc = self.list.description
        self.list.destroySelf()
        self.message.write('List %s deleted' % desc)
        self.redirect('./')
