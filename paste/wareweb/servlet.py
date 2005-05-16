import re
import urllib
from paste import httpexceptions
import time
import timeinterval
import cgifields
import event
import classinit
from UserDict import UserDict

__all__ = ['Servlet']

class Servlet(object):

    app_name = 'app'
    listeners = []

    __metaclass__ = classinit.ClassInitMeta

    def __classinit__(cls, new_attrs):
        if not new_attrs.has_key('listeners'):
            cls.listeners = cls.listeners[:]
        for attr, value in new_attrs.items():
            cls.add_attr(attr, value, set=False)
        classinit.build_properties(cls, new_attrs)

    @classmethod
    def add_attr(cls, attr, value, set=True):
        if set:
            setattr(cls, attr, value)
        if hasattr(value, '__addtoclass__'):
            value.__addtoclass__(attr, cls)

    def __call__(self, environ, start_response):
        value = event.raise_event('call', self, environ, start_response)
        if value is not event.Continue:
            status, headers, app_iter = value
            start_response(status, headers)
            return app_iter
        self.environ = environ
        self.config = self.environ['paste.config']
        if self.config.get('app_name'):
            self.app_name = self.config['app_name']
        self._cached_output = []
        self.headers_out = {
            'Content-type': 'text/html; charset=UTF-8'}
        self.status = '200 OK'
        self.cookies_out = {}
        self.request_method = environ['REQUEST_METHOD'].upper()
        self.app_url = self.environ.get('%s.base_url' % self.app_name, '')
        self.app_static_url = self.config.get(
            'static_url', self.app_url + '/static')
        self.path_info = self.environ.get('PATH_INFO', '')
        if self.path_info:
            self.path_parts = filter(None, self.path_info[1:].split('/'))
        else:
            # Note that you have to look at self.path_info to
            # distinguish between '' and '/'
            self.path_parts = []
        self.fields = cgifields.Fields(cgifields.parse_fields(environ))
        self.run()
        headers = []
        for name, value in self.headers_out.items():
            if isinstance(value, list):
                for v in value:
                    headers.append((name, v))
            else:
                headers.append((name, value))
        # @@: cookies
        start_response(self.status, headers)
        return self._cached_output

    @event.wrap_func
    def run(self):
        try:
            self.awake()
            self.respond()
        finally:
            self.sleep()


    @event.wrap_func
    def awake(self, call_setup=True):
        if call_setup:
            self.setup()

    def setup(self):
        pass

    @event.wrap_func
    def respond(self):
        pass

    @event.wrap_func
    def sleep(self, call_teardown=True):
        if call_teardown:
            self.teardown()

    def teardown(self):
        pass

    ############################################################
    ## Request
    ############################################################

    def session__get(self):
        if 'paste.session.factory' in self.environ:
            sess = self.environ['paste.session.factory']()
        elif 'paste.flup_session_service' in self.environ:
            sess = self.environ['paste.flup_session_service'].session
        self.__dict__['session'] = sess
        return sess

    ############################################################
    ## Response
    ############################################################

    def title__get(self):
        return self.__class__.__name__

    def title__set(self, value):
        # Get rid of the property:
        self.__dict__['title'] = value

    def set_cookie(self, cookie_name, value, path='/',
                   expires='ONCLOSE', secure=False):
        c = cookie.Cookie(cookie_name, value, path=path,
                          expires=expires, secure=secure)
        self._cookies_out[cookie_name] = c

    def set_header(self, header_name, header_value):
        header_name = header_name.lower()
        if header_name == 'status':
            self.status = header_value
            return
        self.headers_out[header_name] = header_value

    def add_header(self, header_name, header_value):
        header_name = header_name.lower()
        if header_name == 'status':
            self.status = header_value
            return
        if self.headers_out.has_key(header_name):
            if not isinstance(self.headers_out[header_name], list):
                self.headers_out[header_name] = [self.headers_out[header_name],
                                             header_value]
            else:
                self.headers_out[header_name].append(header_value)
        else:
            self.headers_out[header_name] = header_value

    def write(self, *obj):
        for v in obj:
            if v is None:
                continue
            elif isinstance(v, str):
                self._cached_output.append(v)
            elif isinstance(v, unicode):
                self._cached_output.append(v.encode('utf-8'))
            else:
                self._cached_output.append(unicode(v).encode('utf-8'))
    
    def redirect(self, url, **query_vars):
        if not url.startswith('/') and not abs_regex.search(url):
            url = self.app_url + '/' + url
        if 'status' in query_vars:
            status = query_vars.pop('status')
            if isinstance(status, (str, unicode)):
                status = int(status.split()[0])
        else:
            status = 303
        if query_vars:
            if '?' in url:
                url += '&'
            else:
                url += '?'
            url += urllib.urlencode(query_vars)
        raise httpexceptions.get_exception(status)(
            "This resource has been redirected",
            headers={'Location': url})

abs_regex = re.compile(r'^[a-zA-Z]:')
