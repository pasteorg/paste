
def application(environ, start_response):
    start_response('200 OK', [('Content-type', 'text/plain')])
    body = 'user: %s' % environ.get('app.user')
    body = body.encode('ascii')
    return [body]
