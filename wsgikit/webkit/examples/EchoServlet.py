r"""\
WSGI application

Does things as requested.  Takes variables:

header.header-name=value, like
  header.location=http://yahoo.com

error=code, like
  error=301 (temporary redirect)
  error=assert (assertion error)

environ=true,
  display all the environmental variables, like
  key=str(value)\n

message=string
  display string
"""

# Special WSGI version of WebKit:
from wsgikit.webkit.wkservlet import Page
from wsgikit import httpexceptions

class EchoServlet(Page):

    def writeHTML(self):
        req = self.request()
        headers = {}
        for key, value in req.fields().items():
            if key.startswith('header.'):
                name = key[len('header.'):]
                self.response().setHeader(name, value)
                # @@: I shouldn't have to do this:
                headers[name] = value

        error = req.field('error', None)
        if error and error != 'iter':
            if error == 'assert':
                assert 0, "I am asserting zero!"
            raise httpexceptions.get_exception(
                int(error), headers=headers)
        
        if req.field('environ', None):
            items = req.environ().items()
            items.sort()
            self.response().setHeader('content-type', 'text/plain')
            for name, value in items:
                self.write('%s=%s\n' % (name, value))
            return

        if req.hasField('message'):
            self.response().setHeader('content-type', 'text/plain')
            self.write(req.field('message'))
            return

        self.write('hello world!')
