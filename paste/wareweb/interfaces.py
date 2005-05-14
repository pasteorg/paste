"""
Descriptions of the main interfaces in Wareweb.  These aren't formal
interfaces, they are just here for documentation purposes.
"""

class IServlet:

    """
    Response method sequence
    ------------------------

    These methods are called roughly in order to produce the response.
    """

    def __call__(environ, start_response):
        """
        Implementation of the WSGI application interface.  Instances
        of IServlet are WSGI applications.

        Calls event ``call`` with ``environ`` and ``start_response``,
        which may return (status_headers, app_iter) and thus abort the
        rest of the call.
        """

    def run():
        """
        'Runs' the request.  This typically just calls ``awake()``,
        ``respond()`` and ``sleep()``.  Error handlers could be added
        here by subclasses.
        
        Wrapped as event (wrapped methods call ``start_method_name``
        and ``end_method_name``).
        """

    def awake(call_setup=True):
        """
        Called at beginning of request.  SHOULD NOT produce output.
        If ``call_setup`` is true then ``.setup()`` will be called.
        ``SitePage`` classes (that is, abstract subclasses of
        ``Servlet``) should override this method and not ``setup``.
        
        Wrapped as event.
        """

    def setup():
        """
        Called at beginning of requests.  Subclasses do not need to
        call the superclass implementation.  This is where individual
        (non-abstract) servlets typically do their setup.
        """

    def respond():
        """
        Called after ``.awake()``, this typically produces the body of
        the response.  Some components may intercept this method
        (e.g., components that want to take over the body of the
        response, like templating components).
        
        Wrapped as event.
        """

    def sleep(call_teardown=True):
        """
        Called at the end of a request, to clean up resources.  Called
        regardless of exceptions in ``.awake()`` or ``.respond()``, so
        implementations should be careful not to assume all resources
        have been successfully set up.  Like ``awake`` this calls
        ``.teardown()`` if ``call_teardown`` is true; abstract classes
        should override this method and not ``teardown``.

        Wrapped as event.
        """

    def teardown():
        """
        Resource cleanup at the end of request.  Subclasses do not
        need to call the superclass implementation.
        """

    """
    Request Attributes
    ------------------

    These attributes describe the request
    """

    environ = """
    The WSGI environment.  Contains typical CGI variables, in addition
    to any WSGI extensions.
    """
    
    config = """
    The Paste configuration object; a dictionary-like object.
    """

    app_url = """
    The URL (usually not fully qualified) of this application.  This
    looks in the environmental variable ``<app_name>.base_url``.
    The default ``app_name`` is ``"app"``, and this requires a
    ``urlparser_hook`` in ``__init__.py`` to set accurately, which
    would look like::

        app_name = 'app'
        def urlparse_hook(environ):
            key = '%s.base_url' % app_name
            if not key in environ:
                environ[key] = environ['SCRIPT_NAME']
    """

    path_info = """
    The value of environ['PATH_INFO'] -- all the URL that comes after
    this servlet's location.
    """

    path_parts = """
    A list of path parts; essentially ``path_info.split('/')``
    """

    fields = """
    A dictionary-like object of all the request fields (both GET and
    POST variables, folded together).

    You can also get variables as attributes (which default to None).

    Also has a ``.getlist(name)`` method, which returns the variable
    as a list (i.e., if missing the return value is ``[]``; if one
    string value the return value is ``[value]``)
    """

    """
    Response Methods
    ----------------

    These methods are used to create the response
    """

    title = """
    Attribute that returns the title of this page.  Default
    implementation returns the class's name.
    """

    session = """
    The session object.  This is a dictionary-like object where values
    are persisted through multiple requests (using a cookie).
    """

    def set_cookie(cookie_name, value, path='/', expires='ONCLOSE',
                   secure=False):
        """
        Creates the named cookie in the response.

        ``expires`` can be:
        * ``ONCLOSE`` (default: expires when browser is closed)
        * ``NOW`` (for immediate deletion)
        * ``NEVER`` (some time far in the future)
        * A integer value (expiration in seconds)
        * A time.struct_time object
        * A string that starts with ``+`` and describes the time, like
          ``+1w`` (1 week) or ``+1b`` (1 month)
        """

    def set_header(header_name, header_value):
        """
        Sets the named header; overwriting any header that previously
        existed.  The ``Status`` header is specially used to change
        the response status.
        """

    def add_header(header_name, header_value):
        """
        Adds the named header, appending to any previous header that
        might have been set.
        """

    def write(*objs):
        """
        Writes the objects.  ``None`` is written as the empty string,
        and unicode objects are encoded with UTF-8.
        """

    def redirect(url, **query_vars):
        """
        Redirects to the given URL.  If the URL is relative, then it
        will be resolved to be absolute with respect to
        ``self.app_url``.

        The status is 303 by default; a status keyword argument can be
        passed to override this.

        Other variables are appended to the query string, e.g.::

            self.redirect('edit', id=5)

        Will redirect to ``edit?id=5``
        """
        
