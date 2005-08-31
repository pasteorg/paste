# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

"""
Creates a session object; then in your application, use::

    environ['paste.session.factory']()

This will return a dictionary.  The contents of this dictionary will
be saved to disk when the request is completed.  The session will be
created when you first fetch the session dictionary, and a cookie will
be sent in that case.  There's current no way to use sessions without
cookies, and there's no way to delete a session except to clear its
data.

@@: This doesn't do any locking, and may cause problems when a single
session is accessed concurrently.  Also, it loads and saves the
session for each request, with no caching.  Also, sessions aren't
expired.
"""

from Cookie import SimpleCookie
import time
import random
import os
import md5
try:
    import cPickle
except ImportError:
    import pickle as cPickle
import wsgilib

class SessionMiddleware(object):

    def __init__(self, application, global_conf=None, **factory_kw):
        self.application = application
        self.factory_kw = factory_kw

    def __call__(self, environ, start_response):
        session_factory = SessionFactory(environ, **self.factory_kw)
        environ['paste.session.factory'] = session_factory

        def session_start_response(status, headers, exc_info=None):
            if not session_factory.created:
                return start_response(status, headers)
            headers.append(session_factory.set_cookie_header())
            return start_response(status, headers, exc_info)

        app_iter = self.application(environ, session_start_response)
        if session_factory.used:
            return wsgilib.add_close(app_iter, session_factory.close)
        else:
            return app_iter

class SessionFactory(object):

    def __init__(self, environ, cookie_name='_SID_',
                 session_class=None, **session_class_kw):
        self.created = False
        self.used = False
        self.environ = environ
        self.cookie_name = cookie_name
        self.session = None
        self.session_class = session_class or FileSession
        self.session_class_kw = session_class_kw

    def __call__(self):
        self.used = True
        if self.session is not None:
            return self.session.data()
        cookies = wsgilib.get_cookies(self.environ)
        session = None
        if cookies.has_key(self.cookie_name):
            self.sid = cookies[self.cookie_name].value
            try:
                session = self.session_class(self.sid, create=False,
                                             **self.session_class_kw)
            except KeyError:
                # Invalid SID
                pass
        if session is None:
            self.created = True
            self.sid = self.make_sid()
            session = self.session_class(self.sid, create=True,
                                         **self.session_class_kw)
        self.session = session
        return session.data()

    def make_sid(self):
        # @@: need better algorithm
        return (''.join(['%02d' % x for x in time.localtime(time.time())[:6]])
                + '-' + self.unique_id())

    def unique_id(self, for_object=None):
        """
        Generates an opaque, identifier string that is practically
        guaranteed to be unique.  If an object is passed, then its
        id() is incorporated into the generation.  Relies on md5 and
        returns a 32 character long string.
        """
        r = [time.time(), random.random(), os.times()]
        if for_object is not None:
            r.append(id(for_object))
        md5_hash = md5.new(str(r))
        try:
            return md5_hash.hexdigest()
        except AttributeError:
            # Older versions of Python didn't have hexdigest, so we'll
            # do it manually
            hexdigest = []
            for char in md5_hash.digest():
                hexdigest.append('%02x' % ord(char))
            return ''.join(hexdigest)

    def set_cookie_header(self):
        c = SimpleCookie()
        c[self.cookie_name] = self.sid
        c[self.cookie_name]['path'] = '/'
        name, value = str(c).split(': ', 1)
        return (name, value)

    def close(self):
        if self.session is not None:
            self.session.close()

class FileSession(object):
    
    def __init__(self, sid, create=False, session_file_path='/tmp'):
        self.session_file_path = session_file_path
        self.sid = sid
        if not create:
            if not os.path.exists(self.filename()):
                raise KeyError
        self._data = None

    def filename(self):
        return os.path.join(self.session_file_path, self.sid)

    def data(self):
        if self._data is not None:
            return self._data
        if os.path.exists(self.filename()):
            f = open(self.filename(), 'rb')
            self._data = cPickle.load(f)
            f.close()
        else:
            self._data = {}
        return self._data

    def close(self):
        if self._data is not None:
            filename = self.filename()
            if not self._data:
                if os.path.exists(filename):
                    os.unlink(filename)
            else:
                f = open(self.filename(), 'wb')
                cPickle.dump(self._data, f)
                f.close()
