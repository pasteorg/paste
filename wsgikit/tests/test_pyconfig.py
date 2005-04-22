import os
from wsgikit import pyconfig
from py.test import raises

def path(name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'pyconfig_data', name)

def test_load():
    conf = pyconfig.load(path('one.py'))
    assert conf['name1'] == 'n1'
    assert conf['name2'] == "n2"
    raises(KeyError, "conf['name3']")
    
def test_nest():
    conf = pyconfig.load(path('nest1.conf'))
    conf.load(path('nest2.conf'))
    assert conf['a'] == 1
    assert conf['b'] == 2
    assert conf['c'] == 3

def test_derivative():
    conf = pyconfig.Config()
    conf.load_dict({'test1': 'a'})
    assert conf['test1'] == 'a'
    conf.load(path('deriv.conf'))
    assert conf['test1'] == 'a+another'
    conf = pyconfig.Config()
    conf.load_dict({'test1': 'b'})
    conf.load(path('deriv.conf'))
    assert conf['test1'] == 'b+another'
    assert not conf.has_key('os')
    
def test_command():
    conf = pyconfig.load(path('one.py'))
    extra = conf.load_commandline(
        ['-h', '--host', 'localhost', '--port=8080', 'arg1', '-f', 'arg2'],
        bool_options=['help', 'verbose'],
        aliases={'f': 'config_file', 'h': 'help', 'v': 'verbose'})
    assert extra == ['arg1']
    assert conf['name1'] == 'n1'
    assert conf['host'] == 'localhost'
    assert conf['port'] == 8080
    assert conf['config_file'] == 'arg2'
    raises(KeyError, "conf['h']")
    raises(KeyError, "conf['f']")
