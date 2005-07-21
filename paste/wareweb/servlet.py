import re
import urllib
import traceback
import time
from UserDict import UserDict
from Cookie import SimpleCookie
from paste.util import classinit
from paste import httpexceptions
import timeinterval
import cgifields
import event
import cookiewriter

__all__ = ['Servlet']

class ForwardRequest(Exception):
    def __init__(self, app):
        self.application = app

class Servlet(object):

    app_name = 'app'
    listeners = []
    _title = None
    _html_title = None

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
        try:
            status, headers, app_iter = self._process(
                environ, start_response)
        except ForwardRequest, e:
            return e.application(environ, start_response)
        else:
            start_response(status, headers)
            return app_iter

    def _process(self, environ, start_response):
        value = event.raise_event('call', self, environ, start_response)
        if value is not event.Continue:
            status, headers, app_iter = value
            return status, headers, app_iter
        self.environ = environ
        self.config = self.environ['paste.config']
        if self.config.get('app_name'):
            self.app_name = self.config['app_name']
        self._cached_output = []
        self.headers_out = {
            'content-type': 'text/html; charset=UTF-8'}
        self.status = '200 OK'
        self._cookies_out = {}
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
        self.cookies = {}
        if 'HTTP_COOKIE' in environ:
            cookies = SimpleCookie()
            try:
                cookies.load(environ['HTTP_COOKIE'])
            except:
                traceback.print_exc(file=self._environ['wsgi.errors'])
            for key in cookies.keys():
                self.cookies[key] = cookies[key].value
        self.run()
        headers = []
        for name, value in self.headers_out.items():
            if isinstance(value, list):
                for v in value:
                    headers.append((name, v))
            else:
                headers.append((name, value))
        for cookie in self._cookies_out.values():
            headers.append(('Set-Cookie', cookie.header()))
        return self.status, headers, self._cached_output

    @event.wrap_func
    def run(self):
        __traceback_hide__ = 'before_and_this'
        try:
            event.wrap_func(self.awake.im_func)(self)
            event.wrap_func(self.respond.im_func)(self)
        finally:
            event.wrap_func(self.sleep.im_func)(self)

    def awake(self, call_setup=True):
        if call_setup:
            self.setup()

    def setup(self):
        pass

    def respond(self):
        pass

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
        return self._title or self.__class__.__name__

    def title__set(self, value):
        self._title = value

    def html_title__get(self):
        return self._html_title or self.title

    def html_title__set(self, value):
        self._html_title = value

    def set_cookie(self, cookie_name, value, path='/',
                   expires='ONCLOSE', secure=False):
        c = cookiewriter.Cookie(cookie_name, value, path=path,
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
        url = str(url)
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

    def forward_to_wsgiapp(self, app):
        """
        Forwards the request to the given WSGI application
        """
        raise ForwardRequest(app)

abs_regex = re.compile(r'^[a-zA-Z]+:')
