#!/usr/bin/env python

import cgi

form = cgi.FieldStorage()
import os

print 'Content-type: text/html\n'

if form.getvalue('name'):
    print '<html><head><title>Hello!</title></head>'
    print '<body>'
    print '<h1>Hello %s!</h1>' % form['name'].value
else:
    print '<html><head><title>Who is there?</title></head>'
    print '<body>'
    print '<h1>Who is there?</h1>'

print '<form action="%s" method="POST">' % os.environ['SCRIPT_NAME']
print 'What is your name?<br>'
print '<input type="text" name="name" value="%s"><br>' \
      % cgi.escape(form.getvalue('name', ''), 1)
print '<input type="submit" value="That is my name"></form>'
print '</body></html>'
