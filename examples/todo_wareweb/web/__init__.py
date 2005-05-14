from paste.util import thirdparty
thirdparty.add_package('sqlobject')
import sqlobject
from todo_wareweb import db

conns = {}

def urlparser_hook(environ):
    if not environ.has_key('todo_wareweb.base_url'):
        environ['todo_wareweb.base_url'] = environ['SCRIPT_NAME']

def urlparser_wrap(environ, start_response, app):
    db_uri = environ['paste.config']['database']
    first_conn = False
    if db_uri in conns:
        conn = conns[db_uri]
    else:
        first_conn = True
        conns[db_uri] = conn = sqlobject.connectionForURI(db_uri)
    sqlobject.sqlhub.threadConnection = conn
    if first_conn:
        db.check_db()
    # @@: This doesn't allow for using database connections during
    # the application iterator
    try:
        return app(environ, start_response)
    finally:
        sqlobject.sqlhub.threadConnection = None
    
