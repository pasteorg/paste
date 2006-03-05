# (c) 2005-2006 James Gardner <james@pythonweb.org>
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""
Error Document Support
++++++++++++++++++++++

Please note: Full tests are not yet available for this module so you
may not wish to use it in production environments yet.

The middleware in this module can be used to intercept responses with
specified status codes and internally forward the request to an appropriate
URL where the content can be displayed to the user as an error document.

Two middleware are provided:

``forward``
    Intercepts a response with a particular status code and returns the 
    content from a specified URL instead.

``custom_forward``
    Intercepts a response with a particular status code and returns the
    content from the URL specified by a user-defined mapper object
    allowing full control over the forwarding based on status code, 
    message, environ, configuration and any custom arguments specified
    when constructing the middleware.
    
For example the ``custom_forward`` middleware is used in Pylons to redirect 
404, 401 and 403 responses to the error.py controller with the ``code``
and ``message`` as part of the query string. The controller then uses the
code and message to display an appropriate error document.

The mapper used in Pylons looks something like this::

    from urllib import urlencode
    from pylons.util import get_prefix
    
    def error_mapper(code, message, environ, global_conf, **kw):
        codes = [401, 403, 404]
        if not asbool(global_conf.get('debug', 'true')):
            codes.append(500)
        if code in codes:
            url = '%s/error/document/?%s'%(
                get_prefix(environ), 
                urlencode({'message':message, 'code':code})
            )
            return url
        return None

If the configuration is in debug mode the middleware doesn't 
intercept ``500`` status codes, instead allowing the debug display
that is produced earlier in the middleware chain to be displayed to 
the user.

In this case the Pylons ``get_prefix()`` function returns the base part
of the URL so that the redirection will be valid no matter what the
base path of the application is. 
"""

from urllib import urlencode
from urlparse import urlparse

def forward(app, codes):
    """
    Intercepts a response with a particular status code and returns the 
    content from a specified URL instead.
    
    The arguments are:
    
    ``app``
        The WSGI application or middleware chain

    ``codes``
        A dictionary of integer status codes and the URL to be displayed
        if the response uses that code.
        
    For example, you might want to create a static file to display a 
    "File Not Found" message at the URL ``/error404.html`` and then use
    ``forward`` middleware to catch all 404 status codes and display the page
    you created. In this example ``app`` is your exisiting WSGI 
    applicaiton::
        
        # Add the RecursiveMiddleware if it is not already in place
        from paste.recursive import RecursiveMiddleware
        app = RecursiveMiddleware(app)
        
        # Set up the error document forwarding
        from paste.errordocument import forward
        app = forward(app, codes={404:'/error404.html'})
        
    """
    for code in codes:
        if not isinstance(code, int):
            raise TypeError('All status codes should be type int. '
                '%s is not valid'%repr(code))
    def error_codes_mapper(code, message, environ, global_conf, codes):
        if codes.has_key(code):
            return codes[code]
        else:
            return None
    return _StatusBasedRedirect(app, error_codes_mapper, codes=codes)
        
def custom_forward(app, mapper, global_conf={}, **kw):
    """
    Intercepts a response with a particular status code and returns the
    content from the URL specified by a user-defined mapper object
    allowing full control over the forwarding based on status code, 
    message, environ, configuration and any custom parameters specified.
    
    The arguments are:
    
    ``app``
        The WSGI application or middleware chain
        
    ``mapper`` 
        An error document mapper object which will be used to map a code to 
        a URL if the code isn't already found in the dictionary specified by
        ``codes``.

    ``global_conf``
        Optional, the default configuration from your config file
    
    ``**kw`` 
        Optional, any other configuration and extra arguments you wish to 
        pass to middleware will also be passed to the custom mapper object.

    Writing a Mapper Object
    -----------------------
    
    ``mapper`` should be a callable that takes a status code as the
    first parameter, a message as the second, and accepts optional environ, 
    global_conf and kw positional argments afterwards. It should return an
    error message to display or None if the code is not to be intercepted.

    If you wanted to write an application to handle all your error docuemnts
    in a consitent way you might do this::
    
        from paste.errordocument import custom_forward
        from paste.recursive import RecursiveMiddleware
        from urllib import urlencode
        
        def error_mapper(code, message, environ, global_conf, kw)
            if code in [404, 500]:
                params = urlencode({'message':message, 'code':code})
                url = '/error?'%(params)
                return url
            else:
                return None
    
        app = RecursiveMiddleware(
            custom_forward(app, error_mapper=error_mapper),
        )
        
    In the above example a ``404 File Not Found`` status response would be 
    redirected to the URL ``/error?code=404&message=File%20Not%20Found``.
    
    You would have to ensure this URL correctly displayed the error page you
    wanted to display or a static fallback error doucment would be displayed 
    and a description of the error that occured trying to display your error
    document would be logged to the WSGI error stream.
    
    Example
    -------
    
    For example the ``paste.errordocument.forward`` middleware actaully
    uses ``custom_forward``. It looks like this::
    
    def forward(app, codes):
        for code in codes:
            if not isinstance(code, int):
                raise TypeError('All status codes should be type int. '
                    '%s is not valid'%repr(code))
        def error_codes_mapper(code, message, environ, global_conf, codes):
            if codes.has_key(code):
                return codes[code]
            else:
                return None
        return custom_forward(app, error_codes_mapper, codes=codes)
    """
    return _StatusBasedRedirect(app, mapper, global_conf, **kw)

class _StatusBasedRedirect:
    """
    The class that does all the work for the ``error_document_mapper()`` see
    the documentation for ``error_document_mapper`` for details or 
    ``error_document_redirect()`` for an different example of its use.
    """
    def __init__(self, app, mapper, global_conf={}, **kw):
        self.application = app
        self.mapper = mapper
        self.global_conf = global_conf
        self.kw = kw
        self.fallback_template = """
            <html>
            <head>
            <title>Error %(code)s</title>
            </html>
            <body>
            <h1>Error %(code)s</h1>
            <p>%(message)s</p>
            <hr>
            <p>
                Additionally an error occurred trying to produce an 
                error document.  A description of the error was logged
                to <tt>wsgi.errors</tt>.
            </p>
            </body>
            </html>                
        """
        
    def __call__(self, environ, start_response):
        url = []
        code_message = []
        try:
            def change_response(status, headers, exc_info=None):
                new_url = None
                parts = status.split(' ')
                try:
                    code = int(parts[0])
                except ValueError, TypeError:
                    raise Exception(
                        '_StatusBasedRedirect middleware '
                        'received an invalid status code %s'%repr(parts[0])
                    )
                message = ' '.join(parts[1:])
                new_url = self.mapper(
                    code, 
                    message, 
                    environ, 
                    self.global_conf, 
                    self.kw
                )
                if not (new_url == None or isinstance(new_url, str)):
                    raise TypeError(
                        'Expected the url to internally '
                        'redirect to in the _StatusBasedRedirect error_mapper'
                        'to be a string or None, not %s'%repr(new_url)
                    )
                if new_url:
                    url.append(new_url)
                code_message.append([code, message])
                return start_response(status, headers, exc_info)
            app_iter = self.application(environ, change_response)
        except:
            try:
                import sys
                error = str(sys.exc_info()[1])
            except:
                error = ''
            try:
                code, message = code_message[0]
            except:
                code, message = ['','']
            environ['wsgi.errors'].write(
                'Error occurred in _StatusBasedRedirect '
                'intercepting the response: '+str(error)
            )
            return [self.fallback_template%{'message':message,'code':code}]
        else:
            if url:
                url_= url[0]
                new_environ = {}
                for k, v in environ.items():
                    if k != 'QUERY_STRING':
                        new_environ['QUERY_STRING'] = urlparse(url_)[4]
                    else:
                        new_environ[k]=v
                class InvalidForward(Exception):
                    pass
                def eat_start_response(status, headers, exc_info=None):
                    """
                    We don't want start_response to do anything since it
                    has already been called
                    """
                    if status[:3] != '200':
                        raise InvalidForward(
                            "The URL %s to internally forward "
                            "to in order to create an error document did not "
                            "return a '200' status code."%url_
                        )
                forward = environ['paste.recursive.forward']
                old_start_response = forward.start_response
                forward.start_response = eat_start_response
                try:
                    app_iter = forward(url_, new_environ)
                except InvalidForward, e:
                    code, message = code_message[0]
                    environ['wsgi.errors'].write(
                        'Error occurred in '
                        '_StatusBasedRedirect redirecting '
                        'to new URL: '+str(url[0])
                    )
                    return [
                        self.fallback_template%{
                            'message':message,
                            'code':code,
                        }
                    ]
                else:
                    forward.start_response = old_start_response
                    return app_iter
            else:
                return app_iter
