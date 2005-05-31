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
    while parts:
        name += '.' + parts[0]
        try:
            module = import_module(name)
            parts = parts[1:]
        except ImportError:
            break
    obj = module
    while parts:
        try:
            obj = getattr(module, parts[0])
        except AttributeError:
            raise ImportError(
                "Cannot find %s in module %r" % (parts[0], module))
        parts = parts[1:]
    return obj

def import_module(s):
    mod = __import__(s)
    parts = s.split('.')
    for part in parts[1:]:
        mod = getattr(mod, part)
    return mod
