import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from paste.tests.fixture import setup_module
from todo_wareweb.db import *
import sqlobject

def test_index():
    res = app.get('/')
    res.mustcontain('List of Lists')
    for lst in TodoList.select():
        res.mustcontain(lst.description)

def test_make_list():
    res = app.post('/edit_list',
                   params=dict(id='new',
                               _action_='save',
                               description='New list'))
    res = res.follow()
    res.mustcontain('List: New list')
    res.mustcontain('No items to display')
    lists = list(TodoList.selectBy(description='New list'))
    assert len(lists) == 1

def reset_state():
    sqlobject.sqlhub.processConnection = sqlobject.connectionForURI(
        CONFIG['database'])
    for item in TodoItem.select():
        item.destroySelf()
    for lst in TodoList.select():
        lst.destroySelf()
    l1 = TodoList(description='Grocery List')
    TodoItem(todo_list=l1,
             description='Apples')
    TodoItem(todo_list=l1,
             description='Comet',
             done=True)
    TodoItem(todo_list=l1,
             description='Oranges')
    l2 = TodoList(description='Bills to pay')
    TodoItem(todo_list=l2,
             description='Electricity')
    
