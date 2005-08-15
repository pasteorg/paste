"""
Cascades through several applications, so long as applications
return ``404 Not Found``.
"""
import httpexceptions

__all__ = ['Cascade']

class Cascade(object):

    """
    Passed a list of applications, ``Cascade`` will try each of them
    in turn.  If one returns a status code listed in ``catch`` (by
    default just ``404 Not Found``) then the next application is
    tried.

    If all applications fail, then the last application's failure
    response is used.
    """

    def __init__(self, applications, catch=(404,)):
        self.apps = applications
        self.catch_codes = {}
        self.catch_exceptions = []
        for error in catch:
            if isinstance(error, str):
                error = int(error.split(None, 1))
            if isinstance(error, httpexceptions.HTTPException):
                exc = error
                code = error.code
            else:
                exc = httpexceptions.get_exception(error)
                code = error
            self.catch_codes[code] = exc
            self.catch_exceptions.append(exc)
        self.catch_exceptions = tuple(self.catch_exceptions)
                
    def __call__(self, environ, start_response):
        def repl_start_response(status, headers, exc_info=None):
            code = int(status.split(None, 1)[0])
            if code in self.catch_codes:
                raise self.catch_codes[code]
            return start_response(status, headers, exc_info)

        for app in self.apps[:-1]:
            try:
                return app(environ, repl_start_response)
            except self.catch_exceptions:
                pass
        return self.apps[-1](environ, start_response)
