import os
import sys
import imp
import wsgilib
from paste.docsupport import metadata

class NoDefault:
    pass

__all__ = ['URLParser', 'StaticURLParser']

class URLParser(object):

    """
    WSGI middleware

    Application dispatching, based on URL.  An instance of `URLParser` is
    an application that loads and delegates to other applications.  It
    looks for files in its directory that match the first part of
    PATH_INFO; these may have an extension, but are not required to have
    one, in which case the available files are searched to find the
    appropriate file.  If it is ambiguous, a 404 is returned and an error
    logged.

    By default there is a constructor for .py files that loads the module,
    and looks for an attribute ``application``, which is a ready
    application object, or an attribute that matches the module name,
    which is a factory for building applications, and is called with no
    arguments.

    URLParser will also look in __init__.py for special overrides.
    These overrides are:

    ``urlparser_hook(environ)``
        This can modified the environment.  Its return value is ignored,
        and it cannot be used to change the response in any way.  You
        *can* use this, for example, to manipulate SCRIPT_NAME/PATH_INFO
        (try to keep them consistent with the original URL -- but
        consuming PATH_INFO and moving that to SCRIPT_NAME is ok).

    ``urlparser_wrap(environ, start_response, app)``:
        After URLParser finds the application, it calls this function
        (if present).  If this function doesn't call
        ``app(environ, start_response)`` then the application won't be
        called at all!  This can be used to allocate resources (with
        ``try:finally:``) or otherwise filter the output of the
        application.

    ``not_found_hook(environ, start_response)``:
        If no file can be found (*in this directory*) to match the
        request, then this WSGI application will be called.  You can
        use this to change the URL and pass the request back to
        URLParser again, or on to some other application.  This
        doesn't catch all ``404 Not Found`` responses, just missing
        files.

    ``application(environ, start_response)``:
        This basically overrides URLParser completely, and the given
        application is used for all requests.  ``urlparser_wrap`` and
        ``urlparser_hook`` are still called, but the filesystem isn't
        searched in any way.
    """

    _config_index_name = metadata.Config(
        """
        A list of allowed names for the index file (the file served
        for requests that end in ``/``).
        """, default=['index', 'Index', 'main', 'Main'])

    _config_hide_extensions = metadata.Config(
        """
        A list of extensions (with leading ``.``) that should not ever
        be served.""", default=['.pyc', '.bak', '.py~'])

    _config_ignore_extensions = metadata.Config(
        """
        Extensions that will be ignored when searching for a file.  If
        the extension is given explicitly, files with these extensions
        will still be served.""", default=[])

    _config_constructors = metadata.Config(
        """
        A dictionary of extensions as keys, and application constructors
        as values.  Also the key ``dir`` for directories, and ``*`` when
        no other constructor is found.

        Each constructor is called like ``constructor(environ, filename)``
        and should return an application or ``None``.
        """)

    default_options = {
        'index_names': ['index', 'Index', 'main', 'Main'],
        'hide_extensions': ['.pyc', '.bak', '.py~'],
        'ignore_extensions': [],
        'constructors': {},
        }

    parsers_by_directory = {}

    # This is lazily initialized
    init_module = NoDefault

    def __init__(self, directory, base_python_name, add_options=None):
        """
        Create a URLParser object that looks at `directory`.
        `base_python_name` is the package that this directory
        represents, thus any Python modules in this directory will
        be given names under this package.

        `add_options` overrides individual configuration options for
        this instance.
        """
        if os.path.sep != '/':
            directory = directory.replace(os.path.sep, '/')
        self.directory = directory
        self.add_options = add_options
        self.base_python_name = base_python_name

    def __call__(self, environ, start_response):
        environ['paste.urlparser.base_python_name'] = self.base_python_name
        if self.add_options:
            environ.setdefault('paste.urlparser.options', {}).update(
                self.add_options)
        if self.init_module is NoDefault:
            self.init_module = self.find_init_module(environ)
        path_info = environ.get('PATH_INFO', '')
        if not path_info:
            return self.add_slash(environ, start_response)
        if (self.init_module
            and getattr(self.init_module, 'urlparser_hook', None)):
            self.init_module.urlparser_hook(environ)
        orig_path_info = environ['PATH_INFO']
        orig_script_name = environ['SCRIPT_NAME']
        application, filename = self.find_application(environ)
        if not application:
            if (self.init_module
                and getattr(self.init_module, 'not_found_hook', None)
                and environ.get('paste.urlparser.not_found_parser') is not self):
                not_found_hook = self.init_module.not_found_hook
                environ['paste.urlparser.not_found_parser'] = self
                environ['PATH_INFO'] = orig_path_info
                environ['SCRIPT_NAME'] = orig_script_name
                return not_found_hook(environ, start_response)
            if filename is None:
                name, rest_of_path = wsgilib.path_info_split(environ['PATH_INFO'])
                if not name:
                    name = 'one of %s' % ', '.join(
                        self.option(environ, 'index_names') or
                        ['(no index_names defined)'])

                return self.not_found(
                    environ, start_response,
                    'Tried to load %s from directory %s'
                    % (name, self.directory))
            else:
                environ['wsgi.errors'].write(
                    'Found resource %s, but could not construct application\n'
                    % filename)
                return self.not_found(
                    environ, start_response,
                    'Tried to load %s from directory %s'
                    % (filename, self.directory))
        if (self.init_module
            and getattr(self.init_module, 'urlparser_wrap', None)):
            return self.init_module.urlparser_wrap(
                environ, start_response, application)
        else:
            return application(environ, start_response)

    def find_application(self, environ):
        if (self.init_module
            and getattr(self.init_module, 'application', None)
            and not environ.get('paste.urlparser.init_application') == environ['SCRIPT_NAME']):
            environ['paste.urlparser.init_application'] = environ['SCRIPT_NAME']
            return self.init_module.application, None
        name, rest_of_path = wsgilib.path_info_split(environ['PATH_INFO'])
        environ['PATH_INFO'] = rest_of_path
        if name is not None:
            environ['SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '') + '/' + name
        if not name:
            names = self.option(environ, 'index_names') or []
            for index_name in names:
                filename = self.find_file(environ, index_name)
                if filename:
                    break
            else:
                # None of the index files found
                filename = None
        else:
            filename = self.find_file(environ, name)
        if filename is None:
            return None, filename
        else:
            return self.get_application(environ, filename), filename

    def not_found(self, environ, start_response, debug_message=None):
        status, headers, body = wsgilib.error_response(
            environ,
            '404 Not Found',
            'The resource at %s could not be found'
            % wsgilib.construct_url(environ),
            debug_message=debug_message)
        start_response(status, headers)
        return [body]

    def option(self, environ, name):
        return environ.get('paste.urlparser.options', {}).get(
            name, self.default_options.get(name))

    def add_slash(self, environ, start_response):
        """
        This happens when you try to get to a directory
        without a trailing /
        """
        url = wsgilib.construct_url(environ, with_query_string=False)
        url += '/'
        if environ.get('QUERY_STRING'):
            url += '?' + environ['QUERY_STRING']
        status = '301 Moved Permanently'
        status, headers, body = wsgilib.error_response(
            environ,
            status,
            '''
            <p>The resource has moved to <a href="%s">%s</a>.  You
            should be redirected automatically.</p>''' % (url, url))
        start_response(status, headers + [('Location', url)])
        return [body]

    def find_file(self, environ, base_filename):
        possible = []
        """Cache a few values to reduce function call overhead"""
        ignore_extensions = self.option(environ, 'ignore_extensions')
        hide_extensions = self.option(environ, 'hide_extensions')
        for filename in os.listdir(self.directory):
            base, ext = os.path.splitext(filename)
            full_filename = os.path.join(self.directory, filename)
            if (ext in hide_extensions
                or not base):
                continue
            if filename == base_filename:
                possible.append(full_filename)
                continue
            if ext in ignore_extensions:
                continue
            if base == base_filename:
                possible.append(full_filename)
        if not possible:
            #environ['wsgi.errors'].write(
            #    'No file found matching %r in %s\n'
            #    % (base_filename, self.directory))
            return None
        if len(possible) > 1:
            environ['wsgi.errors'].write(
                'Ambiguous URL: %s; matches files %s\n'
                % (wsgilib.construct_url(environ),
                   ', '.join(possible)))
            return None
        return possible[0]

    def get_application(self, environ, filename):
        constructors = self.option(environ, 'constructors')
        if os.path.isdir(filename):
            t = 'dir'
        else:
            t = os.path.splitext(filename)[1]
        constructor = constructors.get(t, constructors.get('*'))
        if constructor is None:
            #environ['wsgi.errors'].write(
            #    'No constructor found for %s\n' % t)
            return constructor
        app = constructor(environ, filename)
        if app is None:
            #environ['wsgi.errors'].write(
            #    'Constructor %s return None for %s\n' %
            #    (constructor, filename))
            pass
        return app

    def register_constructor(cls, extension, constructor):
        """
        Register a function as a constructor.  Registered constructors
        apply to all instances of `URLParser`.

        The extension should have a leading ``.``, or the special
        extensions ``dir`` (for directories) and ``*`` (a catch-all).

        `constructor` must be a callable that takes two arguments:
        ``environ`` and ``filename``, and returns a WSGI application.
        """
        d = cls.default_options['constructors']
        assert not d.has_key(extension), (
            "A constructor already exists for the extension %r (%r) "
            "when attemption to register constructor %r"
            % (extension, d[extension], constructor))
        d[extension] = constructor
    register_constructor = classmethod(register_constructor)

    def get_parser(cls, directory, base_python_name):
        """
        Get a parser for the given directory, or create one if
        necessary.  This way parsers can be cached and reused.
        """
        try:
            return cls.parsers_by_directory[(directory, base_python_name)]
        except KeyError:
            parser = cls(directory, base_python_name)
            cls.parsers_by_directory[(directory, base_python_name)] = parser
            return parser
    get_parser = classmethod(get_parser)

    def find_init_module(self, environ):
        filename = os.path.join(self.directory, '__init__.py')
        if not os.path.exists(filename):
            return None
        return load_module(environ, filename)

    def __repr__(self):
        return '<%s directory=%r; module=%s at %s>' % (
            self.__class__.__name__,
            self.directory,
            self.base_python_name,
            hex(abs(id(self))))

def make_directory(environ, filename):
    base_python_name = environ['paste.urlparser.base_python_name']
    if base_python_name:
        base_python_name += "." + os.path.basename(filename)
    else:
        base_python_name = os.path.basename(filename)
    return URLParser.get_parser(filename, base_python_name)

URLParser.register_constructor('dir', make_directory)

def make_unknown(environ, filename):
    return wsgilib.send_file(filename)

URLParser.register_constructor('*', make_unknown)

def load_module(environ, filename):
    base_python_name = environ['paste.urlparser.base_python_name']
    module_name = os.path.splitext(os.path.basename(filename))[0]
    if base_python_name:
        module_name = base_python_name + '.' + module_name
    return load_module_from_name(environ, filename, module_name,
                                 environ['wsgi.errors'])

def load_module_from_name(environ, filename, module_name, errors):
    if sys.modules.has_key(module_name):
        return sys.modules[module_name]
    init_filename = os.path.join(os.path.dirname(filename), '__init__.py')
    if not os.path.exists(init_filename):
        try:
            f = open(init_filename, 'w')
        except (OSError, IOError), e:
            errors.write(
                'Cannot write __init__.py file into directory %s (%s)\n'
                % (os.path.dirname(filename), e))
            return None
        f.write('#\n')
        f.close()
    fp = None
    if sys.modules.has_key(module_name):
        return sys.modules[module_name]
    if '.' in module_name:
        parent_name = '.'.join(module_name.split('.')[:-1])
        base_name = module_name.split('.')[-1]
        parent = load_module_from_name(environ, os.path.dirname(filename),
                                       parent_name, errors)
    else:
        base_name = module_name
    fp = None
    try:
        fp, pathname, stuff = imp.find_module(
            base_name, [os.path.dirname(filename)])
        module = imp.load_module(module_name, fp, pathname, stuff)
    finally:
        if fp is not None:
            fp.close()
    return module

def make_py(environ, filename):
    module = load_module(environ, filename)
    if not module:
        return None
    if hasattr(module, 'application') and module.application:
        return module.application
    base_name = module.__name__.split('.')[-1]
    if hasattr(module, base_name):
        return getattr(module, base_name)()
    environ['wsgi.errors'].write(
        "Cound not find application or %s in %s\n"
        % (base_name, module))
    return None
    
URLParser.register_constructor('.py', make_py)


class StaticURLParser(object):
    
    """
    Like ``URLParser`` but only serves static files.
    """
    # @@: Should URLParser subclass from this?

    def __init__(self, directory):
        if os.path.sep != '/':
            directory = directory.replace(os.path.sep, '/')
        self.directory = directory

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        if not path_info:
            return self.add_slash(environ, start_response)
        if path_info == '/':
            # @@: This should obviously be configurable
            filename = 'index.html'
        else:
            filename = wsgilib.path_info_pop(environ)
        full = os.path.join(self.directory, filename)
        if not os.path.exists(full):
            return self.not_found(environ, start_response)
        if os.path.isdir(full):
            # @@: Cache?
            return self.__class__(full)(environ, start_response)
        if environ.get('PATH_INFO') and environ.get('PATH_INFO') != '/':
            return self.error_extra_path(environ, start_response)
        return wsgilib.send_file(full)(environ, start_response)

    def add_slash(self, environ, start_response):
        """
        This happens when you try to get to a directory
        without a trailing /
        """
        url = wsgilib.construct_url(environ, with_query_string=False)
        url += '/'
        if environ.get('QUERY_STRING'):
            url += '?' + environ['QUERY_STRING']
        status = '301 Moved Permanently'
        status, headers, body = wsgilib.error_response(
            environ,
            status,
            '''
            <p>The resource has moved to <a href="%s">%s</a>.  You
            should be redirected automatically.</p>''' % (url, url))
        start_response(status, headers + [('Location', url)])
        return [body]
        
    def not_found(self, environ, start_response, debug_message=None):
        status, headers, body = wsgilib.error_response(
            environ,
            '404 Not Found',
            'The resource at %s could not be found'
            % wsgilib.construct_url(environ),
            debug_message=debug_message)
        start_response(status, headers)
        return [body]

    def error_extra_path(self, environ, start_response):
        status, headers, body = wsgilib.error_response(
            environ,
            '500 Bad Request',
            'The trailing path %r is not allowed' % environ['PATH_INFO'])
        start_response(status, headers)
        return [body]
    
    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.directory)
