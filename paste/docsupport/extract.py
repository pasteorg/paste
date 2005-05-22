import types
import inspect
from cStringIO import StringIO
import textwrap
import findmodules
from paste.docsupport import metadata
from paste.util.classinit import ClassInitMeta
from paste.httpexceptions import HTTPException

extractors = []

class Extractor(object):

    __metaclass__ = ClassInitMeta
    match_type = None
    match_level = None

    def __classinit__(cls, new_attrs):
        if cls.__bases__ != (object,):
            if cls.match_level is None:
                extractors.append(cls)
            else:
                extractors.insert(cls.match_level, cls)

    def __init__(self, obj, context):
        self.obj = obj
        self.context = context

    def extract(self):
        raise NotImplementedError

    def applies(cls, obj, context):
        return isinstance(obj, cls.match_type)
    applies = classmethod(applies)

class ModuleExtractor(Extractor):
    
    match_type = types.ModuleType

    def extract(self):
        objs = getattr(self.obj, '__all__', [])
        if not objs:
            return
        self.context.writeheader(self.obj.__name__, type='Module')
        self.context.writedoc(self.obj.__doc__)
        for name in objs:
            self.context.push_name(name)
            self.context.extract(getattr(self.obj, name))
            self.context.pop_name(name)
        self.context.endheader()

class ClassExtractor(Extractor):

    match_type = (type, types.ClassType)
        
    def extract(self):
        self.context.writeheader(self.context.last_name, type='Class')
        self.context.writedoc(self.obj.__doc__)
        attrs = self.getattrs(self.obj)
        for name, value in attrs:
            self.context.push_name(name)
            self.context.extract(value)
            self.context.pop_name(name)
        methods = self.getmethods(self.obj)
        for name, value in methods:
            self.context.push_name(name)
            self.context.extract(value)
            self.context.pop_name(name)
        self.context.endheader()

    def getattrs(self, cls):
        bases = inspect.getmro(cls)
        attrs = {}
        for i, base in enumerate(bases):
            for name, value in base.__dict__.items():
                if not isinstance(value, metadata.DocItem):
                    continue
                if name in attrs:
                    continue
                attrs[name] = (i, value.__creationorder__, value)
        attrs = attrs.items()
        attrs.sort(lambda a, b: cmp(a[1], b[1]))
        return [
            (m[0], m[1][2]) for m in attrs]

    def getmethods(self, cls):
        bases = inspect.getmro(cls)
        methods = {}
        for i, base in enumerate(bases):
            if base.__dict__.has_key('__all__'):
                all = base.__all__ or []
            else:
                all = None
            for name, value in base.__dict__.items():
                if all is not None and name not in all:
                    continue
                if not isinstance(value, types.FunctionType):
                    continue
                if name in methods:
                    continue
                methods[name] = (i, value.func_code.co_firstlineno, value)
        methods = methods.items()
        methods.sort(lambda a, b: cmp(a[1], b[1]))
        return [
            (m[0], m[1][2]) for m in methods]
    
class DetectedExtractor(Extractor):

    def applies(cls, obj, context):
        return isinstance(obj, metadata.DocItem)
    applies = classmethod(applies)
    
    def extract(self):
        self.obj.writeto(self.context)

class MethodExtractor(Extractor):

    match_type = types.FunctionType

    def extract(self):
        if not self.obj.__doc__:
            return
        sig = self.make_sig()
        self.context.writekey('def %s(%s)' % (self.obj.func_name, sig),
                              monospace=False)
        self.context.writedoc(self.obj.__doc__)
        if self.get_attr('proxy'):
            self.context.writedoc(self.get_attr('proxy').__doc__)
        if getattr(self.obj, 'returns', None):
            returns = self.obj.returns
            if isinstance(returns, str):
                returns = self.obj.func_globals[returns]
            self.context.extract(self.obj.returns)
        self.context.endkey()

    def make_sig(self):
        proxy = self.get_attr('proxy')
        args, varargs, varkw, defaults = inspect.getargspec(
            proxy or self.obj)
        sig = []
        args.reverse()
        for arg in args:
            if defaults:
                sig.append('%s=%r' % (arg, defaults[-1]))
                defaults = defaults[:-1]
            else:
                sig.append(arg)
        sig.reverse()
        if varargs:
            sig.append('*%s' % varargs)
        if varkw:
            sig.append('**%s' % varkw)
        return ', '.join(sig)

    def get_attr(self, attr):
        if not getattr(self.obj, attr, None):
            return None
        value = getattr(self.obj, attr)
        if isinstance(value, str):
            value = self.obj.func_globals[value]
        return value

class HTTPExtractor(Extractor):

    match_level = 0

    def extract(self):
        self.context.writekey(self.obj.__name__)
        self.context.write('%s %s\n' % (self.obj.code, self.obj.title))
        self.context.endkey()

    def applies(cls, obj, context):
        return (isinstance(obj, types.ClassType)
                and issubclass(obj, HTTPException))
    applies = classmethod(applies)

############################################################
## Context
############################################################

class DocContext(object):

    headerchars = '+=-~.\'_`'

    def __init__(self):
        self.out = StringIO()
        self.header_level = 0
        self.indent_level = 0
        self.names = []

    def push_name(self, name):
        self.names.append(name)

    def pop_name(self, name=None):
        if name is not None:
            assert self.names[-1] == name, (
                "Out of order pop (popping %r; expected %r)"
                % (self.names[-1], name))
        self.names.pop()

    def last_name__get(self):
        return self.names[-1]
    last_name = property(last_name__get)

    def writeheader(self, name, type=None):
        if self.indent_level:
            self.writekey(name, type=type, monospace=False)
            return
        if type:
            name = '%s: %s' % (type, name)
        self.write(name + '\n')
        self.write(self.headerchars[self.header_level]
                   * len(name))
        self.write('\n\n')
        self.header_level += 1

    def endheader(self):
        if self.indent_level:
            self.endkey()
            return
        self.header_level -= 1
        assert self.header_level >= 0, (
            "Too many endheader() calls.")

    def writedoc(self, doc):
        if doc is None:
            return
        doc = self.clean(doc)
        if not doc:
            return
        self.write(doc)
        self.write('\n\n')

    def writelist(self, seq, header=None, with_titles=False):
        seq = list(seq)
        if not seq:
            return
        if header:
            self.writeheader(header)
        for name, value in seq:
            if with_titles:
                self.writeheader(name)
            value.write(self)
            if with_titles:
                self.endheader()
        if header:
            self.endheader()

    def writekey(self, key, type=None, monospace=True):
        if monospace:
            key = '``%s``' % key
        if type:
            key = '%s: %s' % (type, key)
        self.write('%s:\n' % key)
        self.indent_level += 2

    def endkey(self):
        self.indent_level -= 2
        assert self.indent_level >= 0, (
            "Too many endkeys or dedents (indent %s)" % self.indent_level)

    def write(self, s):
        if self.indent_level:
            self.out.write(self.indent(s, self.indent_level))
        else:
            self.out.write(s)

    def clean(self, s):
        return textwrap.dedent(s).rstrip().lstrip('\n')

    def indent(self, s, indent=2):
        new = '\n'.join([' '*indent + l for l in s.splitlines()])
        if s.endswith('\n'):
            new += '\n'
        return new
    
    def capture(self, obj):
        old_out = self.out
        self.out = StringIO()
        obj.write(self)
        result = self.out.getvalue()
        self.out = old_out
        return result

    def extract(self, obj):
        for extractor in extractors:
            if extractor.applies(obj, self):
                ext = extractor(obj, self)
                ext.extract()
                break
        else:
            print >> sys.stderr, 'No extractor applies to %r\n' % obj

def build_doc(package):
    context = DocContext()
    for module in findmodules.find_modules(package):
        context.extract(module)
    return context.out.getvalue()

if __name__ == '__main__':
    import sys
    from paste.util.import_string import import_module
    base = import_module(sys.argv[1])
    print build_doc(base)
    
