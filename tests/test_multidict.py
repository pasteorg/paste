from paste.util.multidict import MultiDict
from py.test import raises

def test_dict():
    d = MultiDict({'a': 1})
    assert d.items() == [('a', 1)]
    d['b'] = 2
    d['c'] = 3
    assert d.items() == [('a', 1), ('b', 2), ('c', 3)]
    d['b'] = 4
    assert d.items() == [('a', 1), ('c', 3), ('b', 4)]
    d.add('b', 5)
    raises(KeyError, 'd.getone("b")')
    assert d.getall('b') == [4, 5]
    assert d.items() == [('a', 1), ('c', 3), ('b', 4), ('b', 5)]
    del d['b']
    assert d.items() == [('a', 1), ('c', 3)]
    assert d.pop('xxx', 5) == 5
    assert d.getone('a') == 1
    assert d.popitem() == ('c', 3)
    assert d.items() == [('a', 1)]
    item = []
    assert d.setdefault('z', item) is item
    assert d.items() == [('a', 1), ('z', item)]
