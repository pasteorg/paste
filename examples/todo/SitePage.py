import os
from paste.webkit.wkservlet import Page
import api

class SitePage(Page):

    manager = None
    
    def awake(self, trans):
        super(SitePage, self).awake(trans)
        if not getattr(self, 'manager', None):
            datadir = trans.request().environ().get('paste.config',{}).get('datadir','.')
            self.manager = api.Manager.load(root=datadir)
        self.baseURL = trans.request().environ()['todo.base_url']
        self.username = self.session().value('username', None)
        if not self.username and self.loginRequired():
            self.transaction().forward('/login')

    def loginRequired(self):
        return True

    def sleep(self, trans):
        super(SitePage, self).sleep(trans)
        if self.manager:
            self.manager.save()
    
    def preAction(self, actionName):
        pass

    def postAction(self, actionName):
        pass

    def writeStyleSheet(self):
        self.write("""<meta http-equiv="Content-Type" content="text/html;
            charset=ISO-8859-1" />\n""")
        self.write("""<link href="%s/main.css" rel="stylesheet"
            type="text/css" media="screen"/>\n""" % self.baseURL)

    def writeDocType(self):
        self.write("""<?xml version="1.0" encoding="iso-8859-1"?>
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
            "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n""")

    def title(self):
        return "Paste ToDo list test"

    def htBodyArgs(self):
        return ""

    def writeBodyParts(self):
        self.writePreContent()
        self.writeContent()
        self.writePostContent()

    def writePreContent(self):
        self.write("""<h1><img src="%s/check.png" align="absmiddle" />Paste ToDo
            List</h1><hr />""" % self.baseURL)

    def writeContent(self):
        self.write("Blank Page")

    def writePostContent(self):
        self.write("""<p class="faded">Copyright not needed</p><pre>%s</pre>""" % self.htmlEncode(repr(self.manager)))


