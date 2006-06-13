# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Middleware for logging requests, using Apache combined log format
"""

import logging
import time

class TransLogger(object):
    """
    This logging middleware will log all requests as they go through.
    They are, by default, sent to a logger named ``'wsgi'`` at the
    INFO level.

    If ``setup_console_handler`` is true, then messages for the named
    logger will be sent to the console.
    """

    format = ('%(REMOTE_ADDR)s - %(REMOTE_USER)s [%(time)s] '
              '"%(REQUEST_METHOD)s %(REQUEST_URI)s %(HTTP_VERSION)s" '
              '%(status)s %(bytes)s "%(HTTP_REFERER)s" "%(HTTP_USER_AGENT)s"')

    def __init__(self, application,
                 logger=None,
                 format=None,
                 logging_level=logging.INFO,
                 logger_name='wsgi',
                 setup_console_handler=True,
                 set_logger_level=logging.DEBUG):
        if format is not None:
            self.format = format
        self.application = application
        self.logging_level = logging_level
        self.logger_name = logger_name
        if logger is None:
            self.logger = logging.getLogger(self.logger_name)
            if setup_console_handler:
                console = logging.StreamHandler()
                console.setLevel(logging.DEBUG)
                # We need to control the exact format:
                console.setFormatter(logging.Formatter('%(message)s'))
                self.logger.addHandler(console)
                self.logger.propagate = False
            if set_logger_level is not None:
                self.logger.setLevel(set_logger_level)
        else:
            self.logger = logger

    def __call__(self, environ, start_response):
        start = time.localtime()
        def replacement_start_response(status, headers, exc_info=None):
            # @@: Ideally we would count the bytes going by if no
            # content-length header was provided; but that does add
            # some overhead, so at least for now we'll be lazy.
            bytes = None
            for name, value in headers:
                if name.lower() == 'content-length':
                    bytes = value
            self.write_log(environ, start, status, bytes)
            return start_response(status, headers)
        return self.application(environ, replacement_start_response)

    def write_log(self, environ, start, status, bytes):
        req_uri = environ.get('SCRIPT_NAME', '') + environ.get('PATH_INFO')
        if environ.get('QUERY_STRING'):
            req_uri += '?'+environ['QUERY_STRING']
        if bytes is None:
            bytes = '-'
        d = {
            'REMOTE_ADDR': environ.get('REMOTE_ADDR') or '-',
            'REMOTE_USER': environ.get('REMOTE_USER') or '-',
            'REQUEST_METHOD': environ['REQUEST_METHOD'],
            'REQUEST_URI': req_uri,
            'HTTP_VERSION': 'HTTP/1.0', # @@ Fix
            'time': time.strftime('%a %b %d %H:%M:%S %Y', start),
            'status': status.split(None, 1)[0],
            'bytes': bytes,
            'HTTP_REFERER': environ.get('HTTP_REFERER', '-'),
            'HTTP_USER_AGENT': environ.get('HTTP_USER_AGENT', '-'),
            }
        message = self.format % d
        self.logger.log(self.logging_level, message)
