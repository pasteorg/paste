# Slightly modified tests from the original cgi test module.

# Copyright © 2001-2023 Python Software Foundation; All Rights Reserved.

import sys
import tempfile
from collections import namedtuple
from io import BytesIO

import pytest

from paste.util import field_storage
from paste.util.field_storage import FieldStorage, parse_header


class HackedSysModule:
    # The regression test will have real values in sys.argv, which
    # will completely confuse the test of the field_storage module
    argv = []
    stdin = sys.stdin


field_storage.sys = HackedSysModule()


parse_strict_test_cases = [
    ("", {}),
    ("&", ValueError("bad query field: ''")),
    ("&&", ValueError("bad query field: ''")),
    # Should the next few really be valid?
    ("=", {}),
    ("=&=", {}),
    # This rest seem to make sense
    ("=a", {'': ['a']}),
    ("&=a", ValueError("bad query field: ''")),
    ("=a&", ValueError("bad query field: ''")),
    ("=&a", ValueError("bad query field: 'a'")),
    ("b=a", {'b': ['a']}),
    ("b+=a", {'b ': ['a']}),
    ("a=b=a", {'a': ['b=a']}),
    ("a=+b=a", {'a': [' b=a']}),
    ("&b=a", ValueError("bad query field: ''")),
    ("b&=a", ValueError("bad query field: 'b'")),
    ("a=a+b&b=b+c", {'a': ['a b'], 'b': ['b c']}),
    ("a=a+b&a=b+a", {'a': ['a b', 'b a']}),
    ("x=1&y=2.0&z=2-3.%2b0", {'x': ['1'], 'y': ['2.0'], 'z': ['2-3.+0']}),
    ("Hbc5161168c542333633315dee1182227:key_store_seqid=400006&cuyer=r"
     "&view=bustomer&order_id=0bb2e248638833d48cb7fed300000f1b"
     "&expire=964546263&lobale=en-US&kid=130003.300038&ss=env",
     {'Hbc5161168c542333633315dee1182227:key_store_seqid': ['400006'],
      'cuyer': ['r'],
      'expire': ['964546263'],
      'kid': ['130003.300038'],
      'lobale': ['en-US'],
      'order_id': ['0bb2e248638833d48cb7fed300000f1b'],
      'ss': ['env'],
      'view': ['bustomer'],
      }),

    ("group_id=5470&set=custom&_assigned_to=31392&_status=1"
     "&_category=100&SUBMIT=Browse",
     {'SUBMIT': ['Browse'],
      '_assigned_to': ['31392'],
      '_category': ['100'],
      '_status': ['1'],
      'group_id': ['5470'],
      'set': ['custom'],
      })
    ]


def gen_result(data, environ):
    encoding = 'latin-1'
    fake_stdin = BytesIO(data.encode(encoding))
    fake_stdin.seek(0)
    form = FieldStorage(fp=fake_stdin, environ=environ, encoding=encoding)
    return {k: form.getlist(k) if isinstance(v, list) else v.value
            for k, v in dict(form).items()}


def test_fieldstorage_properties():
    fs = FieldStorage()
    assert not fs
    assert "FieldStorage" in repr(fs)
    assert list(fs) == list(fs.keys())
    fs.list.append(namedtuple('MockFieldStorage', 'name')('fieldvalue'))
    assert fs


def test_fieldstorage_invalid():
    with pytest.raises(TypeError):
        FieldStorage("not-a-file-obj", environ={"REQUEST_METHOD": "PUT"})
    with pytest.raises(TypeError):
        FieldStorage("foo", "bar")
    fs = FieldStorage(headers={'content-type': 'text/plain'})
    with pytest.raises(TypeError):
        bool(fs)


def test_strict():
    for orig, expect in parse_strict_test_cases:
        env = {'QUERY_STRING': orig}
        fs = FieldStorage(environ=env)
        if isinstance(expect, dict):
            # test dict interface
            assert len(expect) == len(fs)
            assert len(expect.keys()) == len(fs.keys())
            assert fs.getvalue("nonexistent field", "default") == "default"
            # test individual fields
            for key in expect.keys():
                expect_val = expect[key]
                assert key in fs
                if len(expect_val) > 1:
                    assert fs.getvalue(key) == expect_val
                else:
                    assert fs.getvalue(key) == expect_val[0]


def test_separator():
    parse_semicolon = [
        ("x=1;y=2.0", {'x': ['1'], 'y': ['2.0']}),
        ("x=1;y=2.0;z=2-3.%2b0", {'x': ['1'], 'y': ['2.0'], 'z': ['2-3.+0']}),
        (";", ValueError("bad query field: ''")),
        (";;", ValueError("bad query field: ''")),
        ("=;a", ValueError("bad query field: 'a'")),
        (";b=a", ValueError("bad query field: ''")),
        ("b;=a", ValueError("bad query field: 'b'")),
        ("a=a+b;b=b+c", {'a': ['a b'], 'b': ['b c']}),
        ("a=a+b;a=b+a", {'a': ['a b', 'b a']}),
    ]
    for orig, expect in parse_semicolon:
        env = {'QUERY_STRING': orig}
        fs = FieldStorage(separator=';', environ=env)
        if isinstance(expect, dict):
            for key in expect.keys():
                expect_val = expect[key]
                assert key in fs
                if len(expect_val) > 1:
                    assert fs.getvalue(key) == expect_val
                else:
                    assert fs.getvalue(key) == expect_val[0]


def test_fieldstorage_readline():
    # FieldStorage uses readline, which has the capacity to read all
    # contents of the input file into memory; we use readline's size argument
    # to prevent that for files that do not contain any newlines in
    # non-GET/HEAD requests
    class TestReadlineFile:
        def __init__(self, file):
            self.file = file
            self.numcalls = 0

        def readline(self, size=None):
            self.numcalls += 1
            if size:
                return self.file.readline(size)
            else:
                return self.file.readline()

        def __getattr__(self, name):
            file = self.__dict__['file']
            a = getattr(file, name)
            if not isinstance(a, int):
                setattr(self, name, a)
            return a

    f = TestReadlineFile(tempfile.TemporaryFile("wb+"))
    try:
        f.write(b'x' * 256 * 1024)
        f.seek(0)
        env = {'REQUEST_METHOD': 'PUT'}
        fs = FieldStorage(fp=f, environ=env)
        try:
            # if we're not chunking properly, readline is only called twice
            # (by read_binary); if we are chunking properly, it will be called
            # 5 times as long as the chunk size is 1 << 16.
            assert f.numcalls >= 2
        finally:
            fs.file.close()
    finally:
        f.close()


def test_fieldstorage_multipart():
    # Test basic FieldStorage multipart parsing
    env = {
        'REQUEST_METHOD': 'POST',
        'CONTENT_TYPE': f'multipart/form-data; boundary={BOUNDARY}',
        'CONTENT_LENGTH': '558'}
    fp = BytesIO(POSTDATA.encode('latin-1'))
    fs = FieldStorage(fp, environ=env, encoding="latin-1")
    assert len(fs.list) == 4
    expect = [{'name': 'id', 'filename': None, 'value': '1234'},
              {'name': 'title', 'filename': None, 'value': ''},
              {'name': 'file', 'filename': 'test.txt',
               'value': b'Testing 123.\n'},
              {'name': 'submit', 'filename': None, 'value': ' Add '}]
    for x in range(len(fs.list)):
        for k, exp in expect[x].items():
            got = getattr(fs.list[x], k)
            assert got == exp


def test_fieldstorage_multipart_leading_whitespace():
    env = {
        'REQUEST_METHOD': 'POST',
        'CONTENT_TYPE': f'multipart/form-data; boundary={BOUNDARY}',
        'CONTENT_LENGTH': '560'}
    # Add some leading whitespace to our post data that will cause the
    # first line to not be the inner boundary.
    fp = BytesIO(b"\r\n" + POSTDATA.encode('latin-1'))
    fs = FieldStorage(fp, environ=env, encoding="latin-1")
    assert len(fs.list) == 4
    expect = [{'name': 'id', 'filename': None, 'value': '1234'},
              {'name': 'title', 'filename': None, 'value': ''},
              {'name': 'file', 'filename': 'test.txt',
               'value': b'Testing 123.\n'},
              {'name': 'submit', 'filename': None, 'value': ' Add '}]
    for x in range(len(fs.list)):
        for k, exp in expect[x].items():
            got = getattr(fs.list[x], k)
            assert got == exp


def test_fieldstorage_multipart_non_ascii():
    # Test basic FieldStorage multipart parsing
    env = {'REQUEST_METHOD': 'POST',
           'CONTENT_TYPE': f'multipart/form-data; boundary={BOUNDARY}',
           'CONTENT_LENGTH': '558'}
    for encoding in ['iso-8859-1', 'utf-8']:
        fp = BytesIO(POSTDATA_NON_ASCII.encode(encoding))
        fs = FieldStorage(fp, environ=env, encoding=encoding)
        assert len(fs.list) == 1
        expect = [{'name': 'id', 'filename': None, 'value': '\xe7\xf1\x80'}]
        for x in range(len(fs.list)):
            for k, exp in expect[x].items():
                got = getattr(fs.list[x], k)
                assert got == exp


def test_fieldstorage_multipart_maxline():
    # Issue #18167
    maxline = 1 << 16 - 1

    def check(content):
        data = """---123
Content-Disposition: form-data; name="upload"; filename="fake.txt"
Content-Type: text/plain

{}
---123--
""".replace('\n', '\r\n').format(content)
        environ = {
            'CONTENT_LENGTH':   str(len(data)),
            'CONTENT_TYPE':     'multipart/form-data; boundary=-123',
            'REQUEST_METHOD':   'POST',
        }

        assert gen_result(data, environ) == {
            'upload': content.encode('latin1')}
    check('x' * maxline)
    check('x' * maxline + '\r')
    check('x' * maxline + '\r' + 'y' * maxline)


def test_fieldstorage_multipart_w3c():
    # Test basic FieldStorage multipart parsing (W3C sample)
    env = {
        'REQUEST_METHOD': 'POST',
        'CONTENT_TYPE': f'multipart/form-data; boundary={BOUNDARY_W3}',
        'CONTENT_LENGTH': str(len(POSTDATA_W3))}
    fp = BytesIO(POSTDATA_W3.encode('latin-1'))
    fs = FieldStorage(fp, environ=env, encoding="latin-1")
    assert len(fs.list) == 2
    assert fs.list[0].name == 'submit-name'
    assert fs.list[0].value == 'Larry'
    assert fs.list[1].name == 'files'
    files = fs.list[1].value
    assert len(files) == 2
    expect = [{'name': None, 'filename': 'file1.txt',
               'value': b'... contents of file1.txt ...'},
              {'name': None, 'filename': 'file2.gif',
               'value': b'...contents of file2.gif...'}]
    for x in range(len(files)):
        for k, exp in expect[x].items():
            got = getattr(files[x], k)
            assert got == exp


def test_fieldstorage_part_content_length():
    boundary = "JfISa01"
    postdata = """--JfISa01
Content-Disposition: form-data; name="submit-name"
Content-Length: 5

Larry
--JfISa01"""
    env = {
        'REQUEST_METHOD': 'POST',
        'CONTENT_TYPE': f'multipart/form-data; boundary={boundary}',
        'CONTENT_LENGTH': str(len(postdata))}
    fp = BytesIO(postdata.encode('latin-1'))
    fs = FieldStorage(fp, environ=env, encoding="latin-1")
    assert len(fs.list) == 1
    assert fs.list[0].name == 'submit-name'
    assert fs.list[0].value == 'Larry'


def test_field_storage_multipart_no_content_length():
    fp = BytesIO(b"""--MyBoundary
Content-Disposition: form-data; name="my-arg"; filename="foo"

Test

--MyBoundary--
""")
    env = {
        "REQUEST_METHOD": "POST",
        "CONTENT_TYPE": "multipart/form-data; boundary=MyBoundary",
        "wsgi.input": fp,
    }
    fields = FieldStorage(fp, environ=env)

    assert len(fields["my-arg"].file.read()) == 5


def test_fieldstorage_as_context_manager():
    fp = BytesIO(b'x' * 10)
    env = {'REQUEST_METHOD': 'PUT'}
    with FieldStorage(fp=fp, environ=env) as fs:
        content = fs.file.read()
        assert fs.file.closed is False
    assert fs.file.closed is True
    assert content == 'x' * 10
    with pytest.raises(ValueError, match='I/O operation on closed file'):
        fs.file.read()


_qs_result = {
    'key1': 'value1',
    'key2': ['value2x', 'value2y'],
    'key3': 'value3',
    'key4': 'value4'
}


def test_qs_and_url_encode():
    data = "key2=value2x&key3=value3&key4=value4"
    environ = {
        'CONTENT_LENGTH':   str(len(data)),
        'CONTENT_TYPE':     'application/x-www-form-urlencoded',
        'QUERY_STRING':     'key1=value1&key2=value2y',
        'REQUEST_METHOD':   'POST',
    }
    assert gen_result(data, environ) == _qs_result


def test_max_num_fields():
    # For application/x-www-form-urlencoded
    data = '&'.join(['a=a']*11)
    environ = {
        'CONTENT_LENGTH': str(len(data)),
        'CONTENT_TYPE': 'application/x-www-form-urlencoded',
        'REQUEST_METHOD': 'POST',
    }

    with pytest.raises(ValueError):
        FieldStorage(
            fp=BytesIO(data.encode()),
            environ=environ,
            max_num_fields=10,
        )

    # For multipart/form-data
    data = """---123
Content-Disposition: form-data; name="a"

3
---123
Content-Type: application/x-www-form-urlencoded

a=4
---123
Content-Type: application/x-www-form-urlencoded

a=5
---123--
"""
    environ = {
        'CONTENT_LENGTH':   str(len(data)),
        'CONTENT_TYPE':     'multipart/form-data; boundary=-123',
        'QUERY_STRING':     'a=1&a=2',
        'REQUEST_METHOD':   'POST',
    }

    # 2 GET entities
    # 1 top level POST entities
    # 1 entity within the second POST entity
    # 1 entity within the third POST entity
    with pytest.raises(ValueError):
        FieldStorage(
            fp=BytesIO(data.encode()),
            environ=environ,
            max_num_fields=4,
        )
    FieldStorage(
        fp=BytesIO(data.encode()),
        environ=environ,
        max_num_fields=5,
    )


def test_qs_and_form_data():
    data = """---123
Content-Disposition: form-data; name="key2"

value2y
---123
Content-Disposition: form-data; name="key3"

value3
---123
Content-Disposition: form-data; name="key4"

value4
---123--
"""
    environ = {
        'CONTENT_LENGTH':   str(len(data)),
        'CONTENT_TYPE':     'multipart/form-data; boundary=-123',
        'QUERY_STRING':     'key1=value1&key2=value2x',
        'REQUEST_METHOD':   'POST',
    }
    assert gen_result(data, environ) == _qs_result


def test_qs_and_form_data_file():
    data = """---123
Content-Disposition: form-data; name="key2"

value2y
---123
Content-Disposition: form-data; name="key3"

value3
---123
Content-Disposition: form-data; name="key4"

value4
---123
Content-Disposition: form-data; name="upload"; filename="fake.txt"
Content-Type: text/plain

this is the content of the fake file

---123--
"""
    environ = {
        'CONTENT_LENGTH':   str(len(data)),
        'CONTENT_TYPE':     'multipart/form-data; boundary=-123',
        'QUERY_STRING':     'key1=value1&key2=value2x',
        'REQUEST_METHOD':   'POST',
    }
    result = {**_qs_result,
              'upload': b'this is the content of the fake file\n'}
    assert gen_result(data, environ) == result


def test_parse_header():
    assert parse_header("text/plain") == ("text/plain", {})
    assert parse_header("text/vnd.just.made.this.up ; ") == (
        "text/vnd.just.made.this.up", {})
    assert parse_header("text/plain;charset=us-ascii") == (
        "text/plain", {"charset": "us-ascii"})
    assert parse_header('text/plain ; charset="us-ascii"') == (
        "text/plain", {"charset": "us-ascii"})
    assert parse_header('text/plain ; charset="us-ascii"; another=opt') == (
        "text/plain", {"charset": "us-ascii", "another": "opt"})
    assert parse_header('attachment; filename="silly.txt"') == (
        "attachment", {"filename": "silly.txt"})
    assert parse_header('attachment; filename="strange;name"') == (
        "attachment", {"filename": "strange;name"})
    assert parse_header('attachment; filename="strange;name";size=123;') == (
        "attachment", {"filename": "strange;name", "size": "123"})
    assert parse_header('form-data; name="files"; filename="fo\\"o;bar"') == (
        "form-data", {"name": "files", "filename": 'fo"o;bar'})


BOUNDARY = "---------------------------721837373350705526688164684"
POSTDATA = """-----------------------------721837373350705526688164684
Content-Disposition: form-data; name="id"

1234
-----------------------------721837373350705526688164684
Content-Disposition: form-data; name="title"


-----------------------------721837373350705526688164684
Content-Disposition: form-data; name="file"; filename="test.txt"
Content-Type: text/plain

Testing 123.

-----------------------------721837373350705526688164684
Content-Disposition: form-data; name="submit"

 Add\x20
-----------------------------721837373350705526688164684--
"""

POSTDATA_NON_ASCII = """-----------------------------721837373350705526688164684
Content-Disposition: form-data; name="id"

\xe7\xf1\x80
-----------------------------721837373350705526688164684
"""

# http://www.w3.org/TR/html401/interact/forms.html#h-17.13.4
BOUNDARY_W3 = "AaB03x"
POSTDATA_W3 = """--AaB03x
Content-Disposition: form-data; name="submit-name"

Larry
--AaB03x
Content-Disposition: form-data; name="files"
Content-Type: multipart/mixed; boundary=BbC04y

--BbC04y
Content-Disposition: file; filename="file1.txt"
Content-Type: text/plain

... contents of file1.txt ...
--BbC04y
Content-Disposition: file; filename="file2.gif"
Content-Type: image/gif
Content-Transfer-Encoding: binary

...contents of file2.gif...
--BbC04y--
--AaB03x--
"""
