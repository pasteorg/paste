def application(environ, start_response):
    start_response('200 OK', [('Content-type', 'text/html')])
    body = 'index: %s' % environ['app.user']
    body = body.encode('ascii')
    return [body]

