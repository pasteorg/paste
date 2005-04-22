from SitePage import SitePage

import api

class register(SitePage):

    def loginRequired(self):
        return False

    def writeContent(self):
        self.write("""<form action="%s/register" method="post"> <p><table>
            <tr><td></td> <td>Enter a username and password to use.</td></tr>
            <tr><td>Username:</td> <td><input type="text" name="username">
            </input></td></tr> <tr><td>Password:</td><td><input type="password"
            name="password"> </input></td> <tr><td></td> <td><input
            type="submit" name="_action_submit" value="Sign Up"></td></tr>
            </table></p>""" % self.baseURL)

    def actions(self):
        return ["submit"]

    def submit(self):
        fields = self.request().fields()
        user = api.User(fields['username'], fields['password'])
        self.manager.addUser(user)
        self.session().setValue('username', user.name)
        self.sendRedirectAndEnd("%s/lists" % user.name)

