import cgi
from cStringIO import StringIO
from paste.request import *
from paste.util.multidict import MultiDict

def test_parse_querystring():
    e = {'QUERY_STRING': 'a=1&b=2&c=3&b=4'}
    d = parse_querystring(e)
    assert d == [('a', '1'), ('b', '2'), ('c', '3'), ('b', '4')]
    assert e['paste.parsed_querystring'] == (
        (d, e['QUERY_STRING']))
    e = {'QUERY_STRING': 'a&b&c=&d=1'}
    d = parse_querystring(e)
    assert d == [('a', ''), ('b', ''), ('c', ''), ('d', '1')]

def make_post(body):
    e = {
        'CONTENT_TYPE': 'application/x-www-form-urlencoded',
        'CONTENT_LENGTH': str(len(body)),
        'wsgi.input': StringIO(body),
        }
    return e

def cmp_post(fs, lst):
    if len(lst) != len(fs):
        print 'Lengths do not match: %r vs expected %r' % (
            len(lst), len(fs))
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

def test_parsevars():
    e = make_post('a=1&b=2&c=3&b=4')
    cur_input = e['wsgi.input']
    d = parse_formvars(e)
    assert isinstance(d, MultiDict)
    assert cmp_post(d, [('a', '1'), ('b', '2'), ('c', '3'), ('b', '4')])
    assert e['paste.parsed_formvars'] == (
        (d, e['wsgi.input']))
    assert e['wsgi.input'] is not cur_input
    cur_input.seek(0)
    assert e['wsgi.input'].read() == cur_input.read()
