"""
Python-syntax configuration loader and abstractor

Usage::

    conf = Config()
    conf.load('file1.py')
    conf.load('file2.py')

Loads files as Python files, gets all global variables as configuration
keys.  You can load multiple files, which will overwrite previous
values (but will not delete previous values).  You can use attribute
or dictionary access to get values.
"""

import types
import os
import sys
from paste.util import thirdparty
UserDict = thirdparty.load_new_module('UserDict', (2, 3))
from paste.reloader import watch_file
from paste.util.threadinglocal import local
import threading

def load(filename):
    conf = Config()
    conf.load(filename)
    return conf

class NoContext:
    pass

class BadCommandLine(Exception):
    pass

config_local = local()

def local_dict():
    try:
        return config_local.wsgi_dict
    except AttributeError:
        config_local.wsgi_dict = result = {}
        return result

class Config(UserDict.DictMixin):

    def __init__(self, with_default=False):
        self.namespaces = []
        if with_default:
            default_config_fn = os.path.join(os.path.dirname(__file__),
                                             'default_config.conf')
            if os.path.exists(default_config_fn):
                self.load(default_config_fn)

    def __getitem__(self, attr):
        for space in self.namespaces:
            if space.has_key(attr):
                return space[attr]
        raise KeyError(
            "Configuration key %r not found" % attr)

    def __setitem__(self, attr, value):
        self.namespaces[0][attr] = value

    def keys(self):
        keys = {}
        for ns in self.namespaces:
            for key in ns.keys():
                keys[key] = None
        return keys.keys()

    def copy(self):
        namespaces = [d.copy() for d in self.namespaces]
        new = self.__class__()
        new.namespaces = namespaces
        return new

    def read_file(self, filename, namespace=None,
                  load_self=True):
        special_keys = ('__file__', 'load', 'include')
        watch_file(filename)
        f = open(filename, 'rb')
        content = f.read()
        f.close()
        if not namespace:
            namespace = {}
        old_values = {}
        for key in special_keys:
            old_values[key] = namespace.get(key)
        if load_self:
            for key in self:
                namespace[key] = self[key]
        orig = namespace.copy()
        namespace['__file__'] = os.path.abspath(filename)
        namespace['load'] = self.make_loader(filename, namespace)
        namespace['include'] = self.make_includer(filename, namespace)
        content = content.replace("\r\n","\n")
        exec content in namespace
        if load_self:
            for name in namespace.keys():
                if (hasattr(__builtins__, name)
                    or name.startswith('_')):
                    del namespace[name]
                    continue
                if orig.has_key(name) and namespace[name] is orig[name]:
                    del namespace[name]
                    continue
                if isinstance(namespace[name], types.ModuleType):
                    del namespace[name]
                    continue
        for key, value in old_values.items():
            if value is None and namespace.has_key(key):
                del namespace[key]
            elif value is not None:
                namespace[key] = value
        return namespace

    def make_loader(self, relative_to, namespace):
        def load(filename):
            filename = os.path.join(os.path.dirname(relative_to),
                                    filename)
            return self.read_file(filename, namespace=namespace.copy())
        return load

    def make_includer(self, relative_to, namespace):
        def include(filename):
            filename = os.path.join(os.path.dirname(relative_to),
                                    filename)
            self.read_file(filename, namespace=namespace,
                           load_self=False)
        return include

    def load(self, filename, default=False):
        namespace = self.read_file(filename)
        self.load_dict(namespace, default)

    def load_dict(self, d, default=False):
        if default:
            self.namespaces.insert(default, d)
        else:
            self.namespaces.insert(0, d)
    
    def load_commandline(self, items, bool_options, aliases={}, default=False):
        """
        Loads options from the command line.  bool_options take no arguments,
        everything else is supposed to take arguments.  aliases is a mapping
        of arguments to other arguments.  All -'s are turned to _, like
        --config-file=... becomes config_file.  Any extra arguments are
        returned as a list.
        """
        options = {}
        args = []
        while items:
            if items[0] == '--':
                args.extend(items[1:])
                break
            elif items[0].startswith('--'):
                name = items[0][2:]
                value = None
                if '=' in name:
                    name, value = name.split('=', 1)
                name = aliases.get(name, name)
                if (name in bool_options
                    or name.replace('-', '_') in bool_options):
                    if value is not None:
                        raise BadCommandLine(
                            "%s does not take any arguments"
                            % items[0])
                    options[name] = True
                    items.pop(0)
                    continue
                if value is None:
                    if len(items) <= 1:
                        raise BadCommandLine(
                            "%s takes an argument, but no argument given"
                            % items[0])
                    value = items[1]
                    items.pop(0)
                items.pop(0)
                value = self.convert_commandline(value)
                options[name] = value
            elif items[0].startswith('-'):
                orig = items[0]
                name = items[0][1:]
                items.pop(0)
                if '=' in name:
                    raise BadCommandLine(
                        "Single-character options may not have arguments (%r)"
                        % orig)
                for i in range(len(name)):
                    op_name = aliases.get(name[i], name[i])
                    if op_name in bool_options:
                        options[op_name] = True
                    else:
                        if i != len(name)-1:
                            raise BadCommandLine(
                                "-%s takes an argument, it cannot be followed "
                                "by other options (in %s)"
                                % (name[i], orig))
                        if not items:
                            raise BadCommandLine(
                                "-%s takes an argument, but no argument given"
                                % name[i])
                        value = self.convert_commandline(items[0])
                        items.pop(0)
                        options[op_name] = value
                        break
            else:
                args.append(items[0])
                items.pop(0)
        for key in options.keys():
            options[key.replace('-', '_')] = options[key]
        self.load_dict(options, default)
        return args

    def convert_commandline(self, value):
        try:
            return int(value)
        except ValueError:
            pass
        return value

def setup_config(filename, add_config=None):
    conf = Config(with_default=True)
    if add_config:
        if isinstance(add_config, (str, unicode)):
            conf.load(add_config)
        else:
            conf.load_dict(add_config)
    conf.load(filename)
    if conf.get('sys_path'):
        update_sys_path(conf['sys_path'], conf['verbose'])
    from paste import CONFIG
    CONFIG.push_process_config(conf)
    return conf

def update_sys_path(paths, verbose):
    if isinstance(paths, (str, unicode)):
        paths = [paths]
    for path in paths:
        path = os.path.abspath(path)
        if path not in sys.path:
            if verbose:
                print 'Adding %s to path' % path
            sys.path.insert(0, path)
        
class DispatchingConfig(object):

    """
    This is a configuration object that can be used globally,
    imported, have references held onto.  The configuration may differ
    by thread (or may not).

    Specific configurations are registered (and deregistered) either
    for the process or for threads.
    """

    # @@: What should happen when someone tries to add this
    # configuration to itself?  Probably the conf should become
    # resolved, and get rid of this delegation wrapper

    _constructor_lock = threading.Lock()

    def __init__(self):
        self._constructor_lock.acquire()
        try:
            self.dispatching_id = 0
            while 1:
                self._local_key = 'paste.processconfig_%i' % self.dispatching_id
                if not local_dict().has_key(self._local_key):
                    break
                self.dispatching_id += 1
        finally:
            self._constructor_lock.release()
        self._process_configs = []

    def push_thread_config(self, conf):
        """
        Make ``conf`` the active configuration for this thread.
        Thread-local configuration always overrides process-wide
        configuration.

        This should be used like:

        conf = make_conf()
        dispatching_config.push_thread_config(conf)
        try:
            ... do stuff ...
        finally:
            dispatching_config.pop_thread_config(conf)
        """
        local_dict().setdefault(self._local_key, []).append(conf)

    def pop_thread_config(self, conf=None):
        """
        Remove a thread-local configuration.  If ``conf`` is given,
        it is checked against the popped configuration and an error
        is emitted if they don't match.
        """
        self._pop_from(local_dict()[self._local_key], conf)

    def _pop_from(self, lst, conf):
        popped = lst.pop()
        if conf is not None and popped is not conf:
            raise AssertionError(
                "The config popped (%s) is not the same as the config "
                "expected (%s)"
                % (popped, conf))

    def push_process_config(self, conf):
        """
        Like push_thread_config, but applies the configuration to
        the entire process.
        """
        self._process_configs.append(conf)

    def pop_process_config(self, conf=None):
        self._pop_from(self._process_config, conf)
            
    def __getattr__(self, attr):
        conf = self.current_conf()
        if not conf:
            raise AttributeError(
                "No configuration has been registered for this process "
                "or thread")
        return getattr(conf, attr)

    def current_conf(self):
        thread_configs = local_dict().get(self._local_key)
        if thread_configs:
            return thread_configs[-1]
        elif self._process_configs:
            return self._process_configs[-1]
        else:
            return None

    def __getitem__(self, key):
        # I thought __getattr__ would catch this, but apparently not
        conf = self.current_conf()
        if not conf:
            raise TypeError(
                "No configuration has been registered for this process "
                "or thread")
        return conf[key]

def make_bool(option):
    """
    Convert a string option to a boolean, e.g. yes/no, true/false
    """
    if not isinstance(option, (str, unicode)):
        return option
    if option.lower() in ('y', 'yes', 't', 'true', '1', 'on'):
        return True
    if option.lower() in ('n', 'no', 'f', 'false', '0', 'off'):
        return False
    raise ValueError(
        "Boolean (yes/no) value expected (got: %r)" % option)

def make_list(option):
    """
    Convert a string to a list, with commas for separators.
    """
    if not option:
        return []
    if not isinstance(option, (str, unicode)):
        if not isinstance(option, (list, tuple)):
            return [option]
        else:
            return option
    return [s.strip() for s in option.split(',')]
