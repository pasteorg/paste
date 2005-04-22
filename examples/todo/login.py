from SitePage import SitePage

class login(SitePage):

    def loginRequired(self):
        return False

    def awake(self, trans):
        super(login, self).awake(trans)
        self.failedLogin = False

    def actions(self):
        return ['submit']

    def writeContent(self):
        if self.failedLogin:
            self.write("""
            <div style="font-color: red">Login incorrect</a>""")
        self.write("""
        <form action="%s/login" method="post">
        <table>
        <tr><td>Username:</td>
        <td><input type="text" name="username"></td></tr>

        <tr><td>Password:</td>
        <td><input type="password" name="password"></td></tr>

        <tr><td></td>
        <td><input type="submit" name="_action_submit" value="Log In">
        </td></tr>
        
        <tr><td></td><td>Enter "guest" and "abc123" to test drive or <a
        href="register">register</a> to get your own user
        account.</td></tr> </table></p>""" % self.baseURL)

    def submit(self):
        field = self.request().field
        trans = self.request().transaction()
        session = self.session()
        username = field('username')
        password = field('password')
        try:
            user = self.manager.getUser(username)
            if password == user.password:
                session.setValue('username', user.name)
                self.sendRedirectAndEnd("%s/lists" % user.name)
                return
        except KeyError:
            pass
        self.failedLogin = True
        self.writeHTML()
