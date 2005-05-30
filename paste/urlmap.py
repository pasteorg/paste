from UserDict import DictMixin
import re
import os
import wsgilib
from docsupport import metadata

__all__ = ['URLMap', 'PathProxyURLMap']

class URLMap(DictMixin):

    """
    URLMap instances are dictionary-like object that dispatch to one
    of several applications based on the URL.

    The dictionary keys are URLs to match (like
    ``PATH_INFO.startswith(url)``), and the values are applications to
    dispatch to.  URLs are matched most-specific-first, i.e., longest
    URL first.  The ``SCRIPT_NAME`` and ``PATH_INFO`` environmental
    variables are adjusted to indicate the new context.
    """
    
    def __init__(self):
        self.applications = []
        self.not_found_application = wsgilib.error_response_app(
            '404 Not Found', 'The resource was not found')

    attr_not_found_application = metadata.Attribute("""
    An application that is run when no other application matches
    the URL.  (Note that the URL ``""`` is also a catch-all URL.)
    By default this application returns a simple 404 Not Found
    result.""")

    norm_url_re = re.compile('//+')

    def normalize_url(self, url, trim=True):
        assert not url or url.startswith('/'), (
            "URL fragments must start with / (you gave %r)" % url)
        url = self.norm_url_re.sub('/', url)
        if trim:
            return url.rstrip('/')
        else:
            return url

    def sort_apps(self):
        """
        Make sure applications are sorted with longest URLs first
        """
        self.applications.sort(
            lambda a, b: cmp(len(b[0]), len(a[0])))

    def __setitem__(self, url, app):
        url = self.normalize_url(url)
        if url in self:
            del self[url]
        self.applications.append((url, app))
        self.sort_apps()

    def __getitem__(self, url):
        url = self.normalize_url(url)
        for app_url, app in self.applications:
            if app_url == url:
                return app
        raise KeyError(
            "No application with the url %r" % url)

    def __delitem__(self, url):
        url = self.normalize_url(url)
        for app_url, app in self.applications:
            if app_url == url:
                self.applications.remove((app_url, url))
                break
        else:
            raise KeyError(
                "No application with the url %r" % url)

    def keys(self):
        return [app_url for app_url, app in self.applications]

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO')
        if not path_info:
            # Kind of just a fast-track for this one case.
            last_url, last_app = self.applications[-1]
            if not last_url:
                return last_app(environ, start_response)
            else:
                return self.not_found_application(environ, start_response)
        path_info = self.normalize_url(path_info, False)
        for app_url, app in self.applications:
            if (path_info == app_url
                or path_info.startswith(app_url + '/')):
                environ['SCRIPT_NAME'] += app_url
                environ['PATH_INFO'] = path_info[len(app_url):]
                return app(environ, start_response)
        return self.not_found_application(environ, start_response)
    
            
class PathProxyURLMap(object):

    """
    This is a wrapper for URLMap that catches any strings that
    are passed in as applications; these strings are treated as
    filenames (relative to `base_path`) and are passed to the
    callable `builder`, which will return an application.

    This is intended for cases when configuration files can be
    treated as applications.

    `base_paste_url` is the URL under which all applications added through
    this wrapper must go.  Use ``""`` if you want this to not
    change incoming URLs.
    """

    def __init__(self, map, base_paste_url, base_path, builder):
        self.map = map
        self.base_paste_url = self.map.normalize_url(base_paste_url)
        self.base_path = base_path
        self.builder = builder
        
    def __setitem__(self, url, app):
        if isinstance(app, (str, unicode)):
            app_fn = os.path.join(self.base_path, app)
            app = self.builder(app_fn)
        url = self.base_paste_url + url
        self.map[url] = app

    def __getattr__(self, attr):
        return getattr(self.map, attr)

    # This is really the only settable attribute
    def not_found_application__get(self):
        return self.map.not_found_application
    def not_found_application__set(self, value):
        self.map.not_found_application = value
    not_found_application = property(not_found_application__get,
                                     not_found_application__set)
        
