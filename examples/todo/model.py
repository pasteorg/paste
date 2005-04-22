"""
Simple To-do Lists

TODO:
  - keep track of the *order* of the items in a list
  - problems everywhere... why can't you have two items with the same name?
  - need to use a serial/id number for each object so that we can reference
    them in the urls by number instead of by name (except for the username
    which makes sense to have in the URLs...)
  - __iter__ating through things?  does that make sense?
  - getList(name) vs. list(name) method names...
  - re-ordering of list items?
  - I know it's just for the sample app, but pickling the manager
    in and out of some local directory?  Is that okay?
  - Why in List.__init__ would it be the list's responsibility to add itself
    to its new owner?  Why wouldn't the owner do that?
"""

import os


class DuplicateUserError(Exception): pass
class DuplicateListError(Exception): pass


class User(object):
    def __init__(self, name, password):
        self.name = name
        self.password = password
        self.lists = {}
    def addList(self, todolist):
        if todolist.name in self.lists:
            raise DuplicateListError("A list by the name %s already exists for user %s" % (todolist.name, self.name))
        self.lists[todolist.name] = todolist
    def getList(self, name):
        return self.lists[name]
    def __iter__(self):
        keys = self.lists.keys()
        keys.sort()
        for key in keys:
            yield key, self.lists[key]


class List(object):
    def __init__(self, name, owner):
        self.name = name
        self.items = {}
        self.owner = owner
        self.owner.addList(self)
    def addItem(self, item):
        if isinstance(item, str):
            item = Item(item)
        self.items[item.name] = item
    def __iter__(self):
        keys = self.items.keys()
        keys.sort()
        for key in keys:
            yield key, self.items[key]


class Item(object):
    def __init__(self, name):
        self.name = name
        self.done = False


class Manager(object):
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.users = {}
    
    def addUser(self, user):
        if user.name in self.users:
            raise DuplicateUserError("A user by the name of %s already exists." % `user.name`)
        self.users[user.name] = user
    
    def getUser(self, username):
        return self.users[username]

    def save(self):
        from cPickle import dump
        dump(self, file(os.path.join(self.root, 'state.pickle'), 'w'))

    def load(cls, root):
        from cPickle import load
        try:
            return load(file(os.path.join(root, 'state.pickle')))
        except IOError:
            return cls(root=root)

    load = classmethod(load)

