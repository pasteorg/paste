from urllib import pathname2url
from urllib2 import unquote
from wsgikit.httpexceptions import HTTPNotFound

from SitePage import SitePage

import api

class lists(SitePage):
        
    def awake(self, trans):
        super(lists, self).awake(trans)
        username = self.request().environ()['todo.username']
        try:
            self.listUser = self.manager.getUser(username)
        except KeyError:
            raise HTTPNotFound
        extra = self.request().extraURLPath()
        if extra and \
                extra[0] == '/' and \
                extra[1:] in self.listUser.lists:
            self.listname = unquote(extra[1:])
            self.writeContent = self.writeContentForOneList
        else:
            self.listname = None
            self.writeContent = self.writeContentForAllLists
    
    def sleep(self, trans):
        self.listUser = None
        super(lists, self).sleep(trans)
    
    def writeContentForOneList(self):
        todolist = self.listUser.getList(self.listname)
        self.write("""
            <h1>%s</h1>
            <ul class="todolist">
            """ % (todolist.name,))
        for name, item in todolist:
            if item.done:
                self.write("""<li class="done">""")
                self.write("""<input type="checkbox" name="%s" checked="checked" />""" % item.name)
            else:
                self.write("""<li class="undone">""")
                self.write("""<input type="checkbox" name="%s" />""" % item.name)
            self.write(""" %s</li>""" % item.name)
        self.write("""
            </ul>
            <form action="../lists/%s" method="post">
            <input type="hidden" name="_action_" value="addItem" />
            <input type="hidden" name="listname" value="%s" />
            <p>
                Add new item: <input type="text" name="itemname" value="" />
                <input type="submit" value="new item" />
            </p>
            </form>
            <script type="text/javascript">
              document.forms[0].itemname.focus();
            </script>
            """ % (todolist.name, todolist.name,))
        
    def writeContentForAllLists(self):
        self.write("""
            <h1>Select a List</h1>
            <ul>
            """)
        for listname, todolist in self.listUser:
            self.write("""
                <li><strong><a href="lists/%(listname)s">%(listname)s</a></strong> (<a href="%(listname)s/delete">obliterate</a>)</li>
                """ % locals())
        self.write("""
            </ul>
            <form action="lists" method="post">
            <input type="hidden" name="_action_" value="addList" />
            <p>
                Add new list: <input type="text" name="listname" value="%s" />
                <input type="submit" value="add list" />
            </p>
            </form>
            """ % self.request().fields().get('listname',''))

    def actions(self):
        return ["addList", "addItem"]

    def addList(self):
        fields = self.request().fields()
        newlist = api.List(fields.get('listname', 'new list'), owner=self.listUser)
        self.sendRedirectAndEnd("/%s/lists/%s" % (self.listUser.name, pathname2url(newlist.name)))

    def addItem(self):
        fields = self.request().fields()
        currentlist = self.listUser.getList(fields['listname'])
        currentlist.addItem(api.Item(fields['itemname']))
        self.sendRedirectAndEnd(
            '%(baseURL)s/%(username)s/lists/%(listname)s'
            % {'baseURL': self.baseURL,
               'username': self.listUser.name,
               'listname': self.listname})
    
