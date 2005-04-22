import os
from wsgikit import wsgilib
from wsgikit.util.thirdparty import add_package
add_package('sqlobject')
import sqlobject

sql_set = False

def urlparser_hook(environ):
    global sql_set
    if not environ.has_key('todo_sql.base_url'):
        environ['todo_sql.base_url'] = environ['SCRIPT_NAME']
    if not sql_set:
        sql_set = True
        db_uri = environ['wsgikit.config']['database']
        sqlobject.sqlhub.processConnection = sqlobject.connectionForURI(
            db_uri)
