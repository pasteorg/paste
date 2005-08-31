# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

"""
'imports' a string -- converts a string to a Python object, importing
any necessary modules and evaluating the expression.  Everything
before the : in an import expression is the module path; everything
after is an expression to be evaluated in the namespace of that
module.

Alternately, if no : is present, then import the modules and get the
attributes as necessary.  Arbitrary expressions are not allowed in
that case.
"""

def eval_import(s):
    if ':' not in s:
        return simple_import(s)
    module_name, expr = s.split(':', 1)
    module = import_module(module_name)
    obj = eval(expr, module.__dict__)
    return obj

def simple_import(s):
    parts = s.split('.')
    module = import_module(parts[0])
    name = parts[0]
    parts = parts[1:]
    last_import_error = None
    while parts:
        name += '.' + parts[0]
        try:
            module = import_module(name)
            parts = parts[1:]
        except ImportError, e:
            last_import_error = e
            break
    obj = module
    while parts:
        try:
            obj = getattr(module, parts[0])
        except AttributeError:
            raise ImportError(
                "Cannot find %s in module %r (stopped importing modules with error %s)" % (parts[0], module, last_import_error))
        parts = parts[1:]
    return obj

def import_module(s):
    mod = __import__(s)
    parts = s.split('.')
    for part in parts[1:]:
        mod = getattr(mod, part)
    return mod
