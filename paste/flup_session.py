"""
Creates a session object; then in your application, use::

    environ['paste.flup_session_service'].session

This will return a dictionary.  The contents of this dictionary will
be saved to disk when the request is completed.  The session will be
created when you first fetch the session dictionary, and a cookie will
be sent in that case.  There's current no way to use sessions without
cookies, and there's no way to delete a session except to clear its
data.
"""

import httpexceptions
import wsgilib
import flup.middleware.session
flup_session = flup.middleware.session

# This is a dictionary of existing stores, keyed by a tuple of
# store type and parameters
store_cache = {}

class SessionMiddleware(object):

    session_classes = {
        'memory': (flup_session.MemorySessionStore,
                   [('session_timeout', 'timeout', int, 60)]),
        'disk': (flup_session.DiskSessionStore,
                 [('session_timeout', 'timeout', int, 60),
                  ('session_dir', 'storeDir', str, '/tmp/sessions')]),
        'shelve': (flup_session.ShelveSessionStore,
                   [('session_timeout', 'timeout', int, 60),
                    ('session_file', 'storeFile', str,
                     '/tmp/session.shelve')]),
        }


    def __init__(self, application):
        self.application = application
        
    def __call__(self, environ, start_response):
        conf = environ['paste.config']

        session_type = conf.get('session_type', 'disk')
        try:
            store_class, store_args = self.session_classes[session_type]
        except KeyError:
            raise KeyError(
                "The session_type %s is unknown (I know about %s)"
                % (session_type,
                   ', '.join(self.session_classes.keys())))
        kw = {}
        param_tuple = [session_type]
        for config_name, kw_name, coercer, default in store_args:
            value = coercer(conf.get(config_name, default))
            param_tuple.append(value)
            kw[kw_name] = value
        param_tuple = tuple(param_tuple)
        if param_tuple in store_cache:
            store = store_cache[param_tuple]
        else:
            store = store_cache[param_tuple] = store_class(**kw)

        cookie_name = conf.get('session_cookie', '_SID_')

        service = flup_session.SessionService(
            store, environ, cookieName=cookie_name,
            fieldName=cookie_name)
        environ['paste.flup_session_service'] = service

        def cookie_start_response(status, headers, exc_info=None):
            service.addCookie(headers)
            print "Added headers:", headers
            return start_response(status, headers, exc_info)

        try:
            app_iter = self.application(environ, cookie_start_response)
        except httpexceptions.HTTPException, e:
            headers = (e.headers or {}).items()
            service.addCookie(headers)
            e.headers = dict(headers)
            service.close()
            raise
        except:
            service.close()
            raise

        return wsgilib.add_close(app_iter, service.close)
            
