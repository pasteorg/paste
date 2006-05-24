from UserDict import DictMixin
import re

__all__ = ['URLMap']

class URLMap(DictMixin):

    """
    URLMap instances are dictionary-like object that dispatch to one
    of several applications based on the URL.

    The dictionary keys are paths to match (like
    PATH_INFO.startswith(path)), and the values are applications to
    dispatch to.  PAths are matched most-specific-first, i.e., longest
    path first.  The SCRIPT_NAME and PATH_INFO environmental variables
    are adjusted to indicate the new context.
    """
    
    def __init__(self, not_found_app=None):
        self.applications = []
        self.not_found_application = not_found_app

    norm_path_re = re.compile('//+')

    def not_found_app(self, environ, start_response):
        full_path = (environ.get('SCRIPT_NAME', '')
                     + environ.get('PATH_INFO', ''))
        body = (
            "<html><head>\n"
            "<title>Not Found</title>\n"
            "</head><body>\n"
            "<h1>Not Found</h1>\n"
            "<p>The page %s was not found. </p>\n"
            "<p><small>(URL mapper failed to find %r)</small></p>"
            "</body></html>"
            % (full_path, environ.get('PATH_INFO')))
        start_response('404 Not Found',
                       [('Content-type', 'text/html')])
        return [body]

    def normalize_path(self, path, trim=True):
        if path.startswith('/'):
            raise ValueError(
                'Mapped paths must not start with / (you gave %r)' % path)
        path = self.norm_path_re.sub('/', path)
        if trim:
            path = path.rstrip('/')
        return path

    def sort_apps(self):
        """
        Make sure applications are sorted with longest URLs first
        """
        self.applications.sort(key=lambda p: -len(p))

    def __setitem__(self, path, app):
        path = self.normalize_path(path)
        if path in self:
            del self[path]
        self.applications.append((path, app))
        self.sort_apps()

    def __getitem__(self, path):
        path = self.normalize_path(path)
        for app_path, app in self.applications:
            if app_path == path:
                return app
        raise KeyError(
            "No application associated with the path %r"
            % path)

    def __delitem__(self, path):
        path = self.normalize_path(path)
        for app_path, app in self.applications:
            if app_path == path:
                self.applications.remove((app_path, app))
                break
        else:
            raise KeyError(
                "No application associated with the path %r" % (path,))

    def keys(self):
        return [app_path
                for app_path, app in self.applications]

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        path_info = self.normalize_path(path_info, False)[1]
        for app_path, app in self.applications:
            if path_info == app_path:
                # We actually have to redirect in this
                # case to add a /...
                return self.add_slash(environ, start_response)
            if path_info.startswith(app_path + '/'):
                environ['SCRIPT_NAME'] += app_path
                environ['PATH_INFO'] = path_info[len(app_path):]
                return app(environ, start_response)
        environ['stdlib.urlmap_object'] = self
        if self.not_found_application is None:
            return self.not_found_app(
                environ, start_response)
        else:
            return self.not_found_application(
                environ, start_response)
        
    
