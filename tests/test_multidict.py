# (c) 2007 Ian Bicking and Philip Jenvey; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
import gc
import io

import pytest

from paste.util.field_storage import FieldStorage
from paste.util.multidict import MultiDict, UnicodeMultiDict

def test_dict():
    d = MultiDict({'a': 1})
    assert d.items() == [('a', 1)]

    d['b'] = 2
    d['c'] = 3
    assert d.items() == [('a', 1), ('b', 2), ('c', 3)]

    d['b'] = 4
    assert d.items() == [('a', 1), ('c', 3), ('b', 4)]

    d.add('b', 5)
    pytest.raises(KeyError, d.getone, "b")
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

    assert d.setdefault('y', 6) == 6

    assert d.mixed() == {'a': 1, 'y': 6, 'z': item}
    assert d.dict_of_lists() == {'a': [1], 'y': [6], 'z': [item]}

    assert 'a' in d
    dcopy = d.copy()
    assert dcopy is not d
    assert dcopy == d
    d['x'] = 'x test'
    assert dcopy != d

    d[(1, None)] = (None, 1)
    assert d.items() == [('a', 1), ('z', []), ('y', 6), ('x', 'x test'),
                         ((1, None), (None, 1))]

def test_unicode_dict():
    _test_unicode_dict()
    _test_unicode_dict(decode_param_names=True)

def _test_unicode_dict(decode_param_names=False):
    d = UnicodeMultiDict(MultiDict({b'a': 'a test'}))
    d.encoding = 'utf-8'
    d.errors = 'ignore'

    if decode_param_names:
        key_str = str
        k = lambda key: key
        d.decode_keys = True
    else:
        key_str = bytes
        k = lambda key: key.encode()

    def assert_unicode(obj):
        assert isinstance(obj, str)

    def assert_key_str(obj):
        assert isinstance(obj, key_str)

    def assert_unicode_item(obj):
        key, value = obj
        assert isinstance(key, key_str)
        assert isinstance(value, str)

    assert d.items() == [(k('a'), 'a test')]
    map(assert_key_str, d.keys())
    map(assert_unicode, d.values())

    d[b'b'] = b'2 test'
    d[b'c'] = b'3 test'
    assert d.items() == [(k('a'), 'a test'), (k('b'), '2 test'), (k('c'), '3 test')]
    list(map(assert_unicode_item, d.items()))

    d[k('b')] = b'4 test'
    assert d.items() == [(k('a'), 'a test'), (k('c'), '3 test'), (k('b'), '4 test')], d.items()
    list(map(assert_unicode_item, d.items()))

    d.add(k('b'), b'5 test')
    pytest.raises(KeyError, d.getone, k("b"))
    assert d.getall(k('b')) == ['4 test', '5 test']
    map(assert_unicode, d.getall('b'))
    assert d.items() == [(k('a'), 'a test'), (k('c'), '3 test'), (k('b'), '4 test'),
                         (k('b'), '5 test')]
    list(map(assert_unicode_item, d.items()))

    del d[k('b')]
    assert d.items() == [(k('a'), 'a test'), (k('c'), '3 test')]
    list(map(assert_unicode_item, d.items()))
    assert d.pop('xxx', '5 test') == '5 test'
    assert isinstance(d.pop('xxx', '5 test'), str)
    assert d.getone(k('a')) == 'a test'
    assert isinstance(d.getone(k('a')), str)
    assert d.popitem() == (k('c'), '3 test')
    d[k('c')] = b'3 test'
    assert_unicode_item(d.popitem())
    assert d.items() == [(k('a'), 'a test')]
    list(map(assert_unicode_item, d.items()))

    item = []
    assert d.setdefault(k('z'), item) is item
    items = d.items()
    assert items == [(k('a'), 'a test'), (k('z'), item)]
    assert isinstance(items[1][0], key_str)
    assert isinstance(items[1][1], list)

    assert isinstance(d.setdefault(k('y'), b'y test'), str)
    assert isinstance(d[k('y')], str)

    assert d.mixed() == {k('a'): 'a test', k('y'): 'y test', k('z'): item}
    assert d.dict_of_lists() == {k('a'): ['a test'], k('y'): ['y test'],
                                 k('z'): [item]}
    del d[k('z')]
    list(map(assert_unicode_item, d.mixed().items()))
    list(map(assert_unicode_item, [(key, value[0]) for \
                                   key, value in d.dict_of_lists().items()]))

    assert k('a') in d
    dcopy = d.copy()
    assert dcopy is not d
    assert dcopy == d
    d[k('x')] = 'x test'
    assert dcopy != d

    d[(1, None)] = (None, 1)
    assert d.items() == [(k('a'), 'a test'), (k('y'), 'y test'), (k('x'), 'x test'),
                         ((1, None), (None, 1))]
    item = d.items()[-1]
    assert isinstance(item[0], tuple)
    assert isinstance(item[1], tuple)

    fs = FieldStorage()
    fs.name = 'thefile'
    fs.filename = 'hello.txt'
    fs.file = io.BytesIO(b'hello')
    d[k('f')] = fs
    ufs = d[k('f')]
    assert isinstance(ufs, FieldStorage)
    assert ufs.name == fs.name
    assert isinstance(ufs.name, str)
    assert ufs.filename == fs.filename
    assert isinstance(ufs.filename, str)
    assert isinstance(ufs.value, bytes)
    assert ufs.value == b'hello'
    ufs = None
    gc.collect()
    assert not fs.file.closed
