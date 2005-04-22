from SitePage import SitePage

import api

class logout(SitePage):

    def awake(self, trans):
        super(logout, self).awake(trans)
        self.session().setValue('username', None)
        self.sendRedirectAndEnd("index")
