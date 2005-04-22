from SitePage import SitePage

import api

class index(SitePage):

    def awake(self, trans):
        super(index, self).awake(trans)
        self.sendRedirectAndEnd(self.username + '/lists')
        return
        username = self.session().value('username', None)
        if username is not None:
            self.sendRedirectAndEnd("%s/lists" % username)
    
    def writeContent(self):
        self.write("""<form action="./" method="post"> <p><table>
            <tr><td>Username:</td> <td><input type="text" name="username">
            </input></td></tr> <tr><td>Password:</td><td><input type="password"
            name="password"> </input></td> <tr><td></td> <td><input
            type="submit" name="_action_submit" value="Log In"></td></tr>
            <tr><td></td><td>Enter "guest" and "abc123" to test drive or <a
            href="register">register</a> to get your own user
            account.</td></tr> </table></p>""")

    def actions(self):
        return ["submit", "logout"]

    def submit(self):
        fields = self.request().fields()
        trans = self.request().transaction()
        session = self.session()
        if fields.has_key('username') and fields.has_key('password'):
            try:
                user = self.manager.getUser(fields['username'])
                if fields['password'] == user.password:
                    session.setValue('username', user.name)
                    self.sendRedirectAndEnd("%s/lists" % user.name)
                    return
            except KeyError:
                pass
        self.awake(self.request().transaction())
        self.writeHTML()

    def logout(self):
        self.session().setValue('username', None)
        self.awake(self.request().transaction())
        self.writeHTML()
