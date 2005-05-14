from paste.wareweb import unpack
from paste.wareweb import cgifields
from cStringIO import StringIO

test_funcs = []

def unpack_test(query, *args, **kw):
    def decorate(func):
        test_funcs.append((func, query, args, kw))
        return func
    return decorate

def test_functions():
    for a1, a2, a3, a4 in test_funcs:
        yield function_test, a1, a2, a3, a4

def function_test(func, query, expect_args, expect_kw):
    spec = unpack.FunctionArgSpec(func)
    if '?' in query:
        path_info, query = query.split('?')
    else:
        path_info = ''
    assert not path_info or path_info.startswith('/')
    path_parts = filter(None, path_info[1:].split('/'))
    fields = cgifields.parse_fields({
        'REQUEST_METHOD': 'GET',
        'QUERY_STRING': query,
        'wsgi.input': StringIO()})
    try:
        args, kw = spec.unpack_args(path_parts, fields)
    except unpack.HTTPBadRequest, e:
        print fields
        print path_parts
        if not expect_kw and len(expect_args) == 1:
            print e
            assert expect_args[0] == str(e)
            return
        raise
    bad_args = []
    if len(expect_args) > args:
        for arg in expect_args[len(args):]:
            bad_args.append('%s: missing' % arg)
    if len(args) > expect_args:
        for arg in args[len(expect_args):]:
            bad_args.append('Bad input positional arg: %s' % arg)
    for i, (got, expected) in enumerate(zip(args, expect_args)):
        if got != expected:
            bad_args.append('Arg %i; got %r != %r'
                            % (i, got, expected))
    for name, value in kw.iteritems():
        if name not in expect_kw:
            bad_args.append('kw %s: not expected' % name)
        elif expect_kw[name] != value:
            bad_args.append('kw %s; got %r != %r'
                            % (name, value, expect_kw[name]))
    for name in expect_kw:
        if name not in kw:
            bad_args.append('kw %s; expected, not gotten' % name)
    if bad_args:
        print "Expected:"
        print expect_args
        print expect_kw
        print "Got:"
        print args
        print kw
        for line in bad_args:
            print line
        assert 0, "Bad arguments"


@unpack_test('name=bob&age=5', name='bob', age_int=5)
@unpack_test('name=joe&age=ten', "Bad variable 'age': invalid literal for int(): ten")
@unpack_test('age=10', "Variable 'name' required")
@unpack_test('name=name&bob=bob', "Variable 'bob' not expected")
@unpack_test('name=name1&name=name2&age=10', "Bad variable 'name': List not expected")
def t(name, age_int):
    pass


@unpack_test('name1=x&name2=x&name3=x', name1='x', name2='x', name3='x')
@unpack_test('/test/this/out?stuff', 'test', 'this', 'out', stuff='')
def t2(*args, **kw):
    pass

@unpack_test('/this/here?x', 'this', 'here', x='')
@unpack_test('/this?x', 'this', x='')
@unpack_test('/?x', 'Not enough parameters on the URL (expected 1 more path segments)')
@unpack_test('/this/here/bad?x', 'Too many parameters on the URL (expected 1 less path segments)')
def t3(arg1_path, arg2_path=None, x=None):
    pass

@unpack_test('a=1', a_list_int=[1])
@unpack_test('')
@unpack_test('a=1&a=2', a_list_int=[1, 2])
@unpack_test('a=b', "Bad variable 'a': invalid literal for int(): b")
def t4(a_list_int=[]):
    pass
