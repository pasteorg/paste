from cStringIO import StringIO
from paste.request import *
import cgi

def test_parse_qs():
    e = {'QUERY_STRING': 'a=1&b=2&c=3&b=4'}
    d = parse_qs(e)
    assert d == [('a', '1'), ('b', '2'), ('c', '3'), ('b', '4')]
    assert e['paste._cached_parse_qs'] == (
        (e['QUERY_STRING'], d))
    e = {'QUERY_STRING': 'a&b&c=&d=1'}
    d = parse_qs(e)
    assert d == [('a', None), ('b', None), ('c', ''), ('d', '1')]

def make_post(body):
    e = {
        'CONTENT_TYPE': 'application/x-www-urlencoded',
        'CONTENT_LENGTH': str(len(body)),
        'wsgi.input': StringIO(body),
        }
    return e

def cmp_post(fs, lst):
    if len(lst) != len(fs.list):
        print 'Lengths do not match: %r vs expected %r' % (
            len(lst), len(fs.list))
        return False
    for fs_item, (expect_name, expect_value) in zip(fs.list, lst):
        if fs_item.name != expect_name:
            print "Names don't match: %r vs expected %r" % (
                fs_item.name, expect_name)
        if fs_item.value != expect_value:
            print "Items don't match: %r vs expected %r" % (
                fs_item.value, expect_value)
            return False
    return True

def test_parse_post():
    e = make_post('a=1&b=2&c=3&b=4')
    cur_input = e['wsgi.input']
    d = parse_post(e)
    assert isinstance(d, cgi.FieldStorage)
    assert cmp_post(d, [('a', '1'), ('b', '2'), ('c', '3'), ('b', '4')])
    assert e['paste._cached_parse_post'] == (
        (e['wsgi.input'], cur_input, d))
    assert e['wsgi.input'] is not cur_input
    cur_input.seek(0)
    assert e['wsgi.input'].read() == cur_input.read()
    
