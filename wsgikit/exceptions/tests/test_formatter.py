from paste.exceptions import formatter
from paste.exceptions import collector
import sys
import os

class Mock(object):
    def __init__(self, **kw):
        for name, value in kw.items():
            setattr(self, name, value)

class Supplement(Mock):

    object = 'test_object'
    source_url = 'http://whatever.com'
    info = 'This is some supplemental information'
    args = ()
    def getInfo(self):
        return self.info

    def __call__(self, *args):
        self.args = args
        return self

class BadSupplement(Supplement):

    def getInfo(self):
        raise ValueError("This supplemental info is buggy")

def call_error(sup):
    1 + 2
    __traceback_supplement__ = (sup, ())
    assert 0, "I am an error"

def raise_error(sup='default'):
    if sup == 'default':
        sup = Supplement()
    for i in range(10):
        __traceback_info__ = i
        if i == 5:
            call_error(sup=sup)

def format(type='html', **ops):
    data = collector.collect_exception(*sys.exc_info())
    report = getattr(formatter, 'format_' + type)(data, **ops)
    return report

formats = ('html', 'text')

def test_excersize():
    for f in formats:
        try:
            raise_error()
        except:
            format(f)

def test_content():
    for f in formats:
        try:
            raise_error()
        except:
            result = format(f)
            print result
            assert 'test_object' in result
            assert 'http://whatever.com' in result
            assert 'This is some supplemental information' in result
            assert 'raise_error' in result
            assert 'call_error' in result
            assert '5' in result
            assert 'test_content' in result

def test_trim():
    current = os.path.abspath(os.getcwd())
    for f in formats:
        try:
            raise_error()
        except:
            result = format(f, trim_source_paths=[(current, '.')])
            assert current not in result
            assert '/test_formatter.py' in result
