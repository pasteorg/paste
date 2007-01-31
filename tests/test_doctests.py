import doctest
from paste.util.import_string import simple_import
import os

filenames = [
    'tests/test_template.txt',
    ]

modules = [
    'paste.util.template',
    ]

options = doctest.ELLIPSIS|doctest.REPORT_ONLY_FIRST_FAILURE

def test_doctests():
    for filename in filenames:
        filename = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            filename)
        yield do_doctest, filename

def do_doctest(filename):
    failure, total = doctest.testfile(
        filename, module_relative=False,
        optionflags=options)
    assert not failure, "Failure in %r" % filename

def test_doctest_mods():
    for module in modules:
        yield do_doctest_mod, module

def do_doctest_mod(module):
    module = simple_import(module)
    failure, total = doctest.testmod(
        module, optionflags=options)
    assert not failure, "Failure in %r" % module
