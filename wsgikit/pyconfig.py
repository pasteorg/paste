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
from wsgikit.util import thirdparty
UserDict = thirdparty.load_new_module('UserDict', (2, 3))

def load(filename):
    conf = Config()
    conf.load(filename)
    return conf

class NoContext:
    pass

class BadCommandLine(Exception):
    pass

class Config(UserDict.DictMixin):

    def __init__(self):
        self.namespaces = []

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

    def load(self, filename, default=False):
        f = open(filename, 'rb')
        content = f.read()
        f.close()
        namespace = {}
        for key in self:
            namespace[key] = self[key]
        orig = namespace.copy()
        namespace['__file__'] = os.path.abspath(filename)
        exec content in namespace
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
        
