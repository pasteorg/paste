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

import cgi
import httpexceptions

def application(environ, start_response):
    form = cgi.FieldStorage(fp=environ['wsgi.input'],
                            environ=environ,
                            keep_blank_values=True)
    headers = {}
    for key in form.keys():
        if key.startswith('header.'):
            headers[key[len('header.'):]] = form[key].value
            
    if form.getvalue('error') and form['error'].value != 'iter':
        if form['error'].value == 'assert':
            assert 0, "I am asserting zero!"
        raise httpexceptions.get_exception(int(form['error'].value))(
            headers=headers)

    if form.getvalue('environ'):
        write = start_response('200 OK', [('Content-type', 'text/plain')])
        items = environ.items()
        items.sort()
        return ['%s=%s\n' % (name, value)
                for name, value in items]

    if form.has_key('message'):
        write = start_response('200 OK', [('Content-type', 'text/plain')])
        write(form['message'].value)
        return []

    if form.getvalue('error') == 'iter':
        return BadIter()
        
    write = start_response('200 OK', [('Content-type', 'text/html')])
    return ['hello world!']

class BadIter(object):
    def __iter__(self):
        assert 0, "I am assert zero in the iterator!"
