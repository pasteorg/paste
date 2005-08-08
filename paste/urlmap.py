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
    
    URLs can also include domains, like ``http://blah.com/foo``, or as
    tuples ``('blah.com', '/foo')``.  This will match domain names; without
    the ``http://domain`` or with a domain of ``None`` any domain will be
    matched (so long as no other explicit domain matches).  """
    
    def __init__(self):
        self.applications = []
        self.not_found_application = self.not_found_app

    attr_not_found_application = metadata.Attribute("""
    An application that is run when no other application matches
    the URL.  (Note that the URL ``""`` is also a catch-all URL.)
    By default this application returns a simple 404 Not Found
    result.""")

    norm_url_re = re.compile('//+')
    domain_url_re = re.compile('^(http|https)://')

    def not_found_app(self, environ, start_response):
        mapper = environ.get('paste.urlmap_object')
        if mapper:
            matches = [p for p, a in mapper.applications]
            extra = 'defined apps: %s' % (
                ', '.join(map(repr, matches)))
        else:
            extra = ''
        extra += '\nSCRIPT_NAME: %r' % environ.get('SCRIPT_NAME')
        extra += '\nPATH_INFO: %r' % environ.get('PATH_INFO')
        app = wsgilib.error_response_app(
            '404 Not Found', 'The resource was not found\n<!-- %s -->'
            % extra)
        return app(environ, start_response)

    def normalize_url(self, url, trim=True):
        if isinstance(url, (list, tuple)):
            domain = url[0]
            url = self.normalize_url(url[1])[1]
            return domain, url
        assert (not url or url.startswith('/') 
                or self.domain_url_re.search(url)), (
            "URL fragments must start with / or http:// (you gave %r)" % url)
        match = self.domain_url_re.search(url)
        if match:
            url = url[match.end():]
            if '/' in url:
                domain, url = url.split('/', 1)
                url = '/' + url
            else:
                domain, url = url, ''
        else:
            domain = None
        url = self.norm_url_re.sub('/', url)
        if trim:
            url = url.rstrip('/')
        return domain, url

    def sort_apps(self):
        """
        Make sure applications are sorted with longest URLs first
        """
        def key(app_desc):
            (domain, url), app = app_desc
            if not domain:
                # Make sure empty domains sort last:
                return -len(url), '\xff'
            else:
                return -len(url), domain
        self.applications.sort(key=key)

    def __setitem__(self, url, app):
        if app is None:
            try:
                del self[url]
            except KeyError:
                pass
            return
        dom_url = self.normalize_url(url)
        if dom_url in self:
            del self[dom_url]
        self.applications.append((dom_url, app))
        self.sort_apps()

    def __getitem__(self, url):
        dom_url = self.normalize_url(url)
        for app_url, app in self.applications:
            if app_url == dom_url:
                return app
        raise KeyError(
            "No application with the url %r (domain: %r; existing: %s)" 
            % (url[1], url[0] or '*', self.applications))

    def __delitem__(self, url):
        url = self.normalize_url(url)
        for app_url, app in self.applications:
            if app_url == url:
                self.applications.remove((app_url, url))
                break
        else:
            raise KeyError(
                "No application with the url %r" % (url,))

    def keys(self):
        return [app_url for app_url, app in self.applications]

    def __call__(self, environ, start_response):
        host = environ.get('HTTP_HOST', environ.get('SERVER_NAME')).lower()
        if ':' in host:
            host = host.split(':', 1)[0]
        path_info = environ.get('PATH_INFO')
        path_info = self.normalize_url(path_info, False)[1]
        for (domain, app_url), app in self.applications:
            if domain and domain != host:
                continue
            if (path_info == app_url
                or path_info.startswith(app_url + '/')):
                environ['SCRIPT_NAME'] += app_url
                environ['PATH_INFO'] = path_info[len(app_url):]
                return app(environ, start_response)
        environ['paste.urlmap_object'] = self
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
        url = self.map.normalize_url(url)
        # @@: This means http://foo.com/bar will potentially
        # match foo.com, but /base_paste_url/bar, which is unintuitive
        url = (url[0] or self.base_paste_url[0], 
               self.base_paste_url[1] + url[1])
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
        
