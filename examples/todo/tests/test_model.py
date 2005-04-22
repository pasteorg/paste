
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from model import User, List, Item, Manager, \
        DuplicateUserError, DuplicateListError


def test_user_creation():
    newuser = User('user1', 'pass')
    assert not newuser.lists
    newlist = List('list1', newuser)
    assert newlist.name in newuser.lists

def test_item_creation():
    newitem = Item('make a new list')
    assert newitem.done == False

def test_list_creation():
    newuser = User('tester', 'pass')
    newlist = List('', newuser)
    assert not newlist.items
    assert newlist.owner.name is newuser.name
    newitem = Item('make a new list')
    assert newitem.done == False
    newlist.addItem(newitem)
    assert len(newlist.items) == 1
    assert newitem.name in newlist.items

class TestListManager:
    
    def setup_class(cls):
        cls.manager = mgr = Manager(root=os.path.join(os.path.dirname(__file__), 'data'))
        print 'cls.manager:', cls.manager.root
        user1 = User('user1', 'pass')
        mgr.addUser(user1)
        user2 = User('user2', 'pass')
        mgr.addUser(user2)
        list1 = List('list1', owner=user1)
        list1.addItem('first step')
        list1.addItem('second step')
        list1.addItem('third step')
        list2 = List('list2', owner=user2)
        
    def test_list_manager(self):
        assert os.path.exists(self.manager.root)
        assert len(self.manager.users) == 2
        assert len(self.manager.getUser('user1').lists) == 1

    def test_list_manipulations(self):
        user1 = self.manager.getUser('user1')
        assert user1.name == 'user1'

    def test_duplicates(self):
        from py.test import raises
        raises(DuplicateUserError, "self.manager.addUser(User('user1', 'pass'))")
        user1 = self.manager.getUser('user1')
        raises(DuplicateListError, "List('list1', owner=user1)")

    def test_simple_persistence(self):
        self.manager.save()
        duped = Manager.load(self.manager.root)
        assert 'user1' in duped.users
        assert 'list2' in duped.getUser('user2').lists

    def teardown_class(cls):
        statefile = os.path.join(cls.manager.root, 'state.pickle')
        if os.path.exists(statefile):
            os.remove(statefile)
