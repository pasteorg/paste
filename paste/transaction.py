# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""
Middleware related to transactions and database connections.

At this time it is very basic; but will eventually sprout all that
two-phase commit goodness that I don't need. 
"""
from paste.httpexceptions import HTTPError, HTTPException

class ConnectionFactory(object):
    """
    Provides a callable interface for connecting to ADBAPI databases in
    a WSGI style (using the environment).  More advanced connection
    factories might use the REMOTE_USER and/or other environment
    variables to make the connection returned depend upon the request.
    """
    def __init__(self, module, *args, **kwargs):
        #assert getattr(module,'threadsaftey',0) > 0
        self.module = module
        self.args = args
        self.kwargs = kwargs

        # deal with database string quoting issues
        self.quote = lambda s: "'%s'" % s.replace("'","''")
        if hasattr(self.module,'PgQuoteString'):
            self.quote = self.module.PgQuoteString

    def __call__(self, environ):
        conn = self.module.connect(*self.args,**self.kwargs)
        conn.__dict__['module'] = self.module
        conn.__dict__['quote'] = self.quote
        return conn

def BasicTransactionHandler(application, factory):
    """
    Provides a simple mechanism for starting a transaction based on the
    factory; and for either committing or rolling back the transaction
    depending on the result.  It checks for the response's current
    status code either through the latest call to start_response; or
    through a HTTPException's code.  If it is a 100, 200, or 300; the
    transaction is committed; otherwise it is rolled back.
    """

    def basic_transaction(environ, start_response):
        conn = factory(environ)
        environ['paste.connection'] = conn
        should_commit = [500]
        def finalizer():
            if should_commit.pop() < 400:
                conn.commit()
            else:
                conn.rollback()
            conn.close()
        def basictrans_start_response(status, headers, exc_info = None):
            should_commit.append(int(status.split(" ")[0]))
            return start_response(status, headers, exc_info)
        try:
            for chunk in application(environ, basictrans_start_response):
                yield chunk
        except Exception, e:
            if isinstance(e,HTTPException):
                should_commit.append(e.code)
            finalizer()
            raise
        finalizer()
    return basic_transaction

__all__ = ['ConnectionFactory','BasicTransactionHandler']

if '__main__' == __name__ and False:
    from pyPgSQL import PgSQL
    factory = ConnectionFactory(PgSQL,database="testing")
    conn = factory(None)
    curr = conn.cursor()
    curr.execute("SELECT now(), %s" % conn.quote("B'n\\'gles"))
    (time,bing) = curr.fetchone()
    print bing, time
