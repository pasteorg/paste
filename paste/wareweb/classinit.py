class classinstancemethod(object):
    """
    Acts like a class method when called from a class, like an
    instance method when called by an instance.  The method should
    take two arguments, 'self' and 'cls'; one of these will be None
    depending on how the method was called.
    """

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, type=None):
        return _methodwrapper(self.func, obj=obj, type=type)

class _methodwrapper(object):

    def __init__(self, func, obj, type):
        self.func = func
        self.obj = obj
        self.type = type

    def __call__(self, *args, **kw):
        assert not kw.has_key('self') and not kw.has_key('cls'), (
            "You cannot use 'self' or 'cls' arguments to a "
            "classinstancemethod")
        return self.func(*((self.obj, self.type) + args), **kw)

    def __repr__(self):
        if self.obj is None:
            return ('<bound class method %s.%s>'
                    % (self.type.__name__, self.func.func_name))
        else:
            return ('<bound method %s.%s of %r>'
                    % (self.type.__name__, self.func.func_name, self.obj))


class ClassInitMeta(type):

    def __new__(meta, class_name, bases, new_attrs):
        cls = type.__new__(meta, class_name, bases, new_attrs)
        if (new_attrs.has_key('__classinit__')
            and not isinstance(cls.__classinit__, staticmethod)):
            setattr(cls, '__classinit__',
                    staticmethod(cls.__classinit__.im_func))
        if hasattr(cls, '__classinit__'):
            cls.__classinit__(cls, new_attrs)
        return cls

def build_properties(cls, new_attrs):
    """
    Given a class and a new set of attributes (as passed in by
    __classinit__), create or modify properties based on functions
    with special names ending in __get, __set, and __del.
    """
    for name, value in new_attrs.items():
        if (name.endswith('__get') or name.endswith('__set')
            or name.endswith('__del')):
            base = name[:-5]
            if hasattr(cls, base):
                old_prop = getattr(cls, base)
                if not isinstance(old_prop, property):
                    raise ValueError(
                        "Attribute %s is a %s, not a property; function %s is named like a property"
                        % (base, type(old_prop), name))
                attrs = {'fget': old_prop.fget,
                         'fset': old_prop.fset,
                         'fdel': old_prop.fdel,
                         'doc': old_prop.__doc__}
            else:
                attrs = {}
            attrs['f' + name[-3:]] = value
            if name.endswith('__get') and value.__doc__:
                attrs['doc'] = value.__doc__
            new_prop = property(**attrs)
            setattr(cls, base, new_prop)
