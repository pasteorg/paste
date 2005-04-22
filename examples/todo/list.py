from SitePage import SitePage

import api

class list(SitePage):
    def writeContent(self):
        self.write("""<h1>User's List""")
        self.write("""<form action="list" method="post"> <p> <table> <tr> <td>
            <input type="text" name="task"> </input> </td> <td> <input
            type="submit" name="_action_add" value="Add"> </td> </tr> </table>
            </p> </form>""")

    def actions(self):
        return ["add"]

    def add(self):
        """
        your code here
        """
        self.awake(self.request().transaction())
        self.writeHTML()



