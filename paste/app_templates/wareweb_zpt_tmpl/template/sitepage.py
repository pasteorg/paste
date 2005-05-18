from paste.wareweb import *
from ZPTKit.zptwareweb import ZPTComponent

class SitePage(Servlet):

    message = Notify()
    template = ZPTComponent()
    app_name = $str_app_name

# This protects "from sitepage import *", since we will no longer
# need these variables:
del ZPTComponent
del Notify
