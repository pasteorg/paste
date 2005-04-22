"""
WSGI application

Automated greeting application.
"""

import cgi

def application(environ, start_response):
    def body():
        form = cgi.FieldStorage(fp=environ['wsgi.input'],
                                environ=environ,
                                keep_blank_values=1)

        if form.getvalue('name'):
            yield ('<html><head><title>Hello!</title></head>\n')
            yield ('<body>\n')
            yield ('<h1>Hello %s!</h1>\n' % form['name'].value)
        else:
            yield ('<html><head><title>Who is there?</title></head>\n')
            yield ('<body>\n')
            yield ('<h1>Who is there?</h1>\n')
        yield ('<form action="%s" method="POST">\n' % environ['SCRIPT_NAME'])
        yield ('What is your name?<br>\n')
        yield ('<input type="text" name="name" value="%s"><br>\n'
              % cgi.escape(form.getvalue('name', ''), 1))
        yield ('<input type="submit" value="That is my name"></form>\n')
        yield ('</body></html>\n')

    start_response('200 OK', [('Content-type', 'text/html')])
    return body()
