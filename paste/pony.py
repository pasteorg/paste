"""
We have a pony
"""

DATA = """
eJyFkkFuxCAMRfdzCisbJxK2D5D2JpbMrlI3XXQZDt9PCG0ySgcWIMT79rcN0XClUJlZRB9jVmci
FmV19khjgRFl0RzrKmqzvY8lRUWFlXvCrD7UbAQR/17NUvGhypAF9og16vWtkC8DzUayS6pN3/dR
ki0OnpzKjUBFpmlC7zVFRNL1rwoq6PWXXQSnIm9WoTzlM2//ke21o5g/l1ckRhiPbkDZXsKIR7l1
36hF9uMhnRiVjI8UgYjlsIKCrXXpcA9iX5y7zMmtG0fUpW61Ssttipf6cp3WARfkMVoYFryi2a+w
o/2dhW0OXfcMTnmh53oR9egzPs+qkpY9IKxdUVRP5wHO7UDAuI6moA2N+/z4vtc2k8B+AIBimVU=
"""

class PonyMiddleware(object):

    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        if path_info == '/pony':
            msg = DATA.decode('base64').decode('zlib')
            msg = '<pre>%s</pre>' % msg
            start_response('200 OK', [('content-type', 'text/html')])
            return [msg]
        else:
            return self.application(environ, start_response)

def make_pony(app, global_conf):
    return PonyMiddleware(app)

