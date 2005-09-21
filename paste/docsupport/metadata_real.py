# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

import sys
import inspect
from itertools import count
from paste.util import import_string
from paste.util.classinit import ClassInitMeta

doc_count = count()

class DocItem(object):

    __metaclass__ = ClassInitMeta

    def __classinit__(cls, new_attrs):
        cls.__creationorder__ = doc_count.next()

    def __init__(self):
        self.__creationorder__ = doc_count.next()
        stack = inspect.stack()
        try:
            while 1:
                name = stack[0][0].f_globals['__name__']
                if name != __name__:
                    break
                stack.pop(0)
            self.call_module_name = name
        finally:
            # Break reference to frames
            stack = None

    def get_object(self, name):
        if '.' in name:
            return import_string.eval_import(name)
        else:
            return getattr(sys.modules[self.call_module_name], name)

    def writeto(self, context):
        raise NotImplementedError

    def writeobj(self, name, context):
        """
        Write the named object to the context
        """
        if name is None:
            return
        obj = self.get_object(name)
        context.push_name(name)
        context.extract(obj)
        context.pop_name(name)
        

class WSGIKey(DocItem):

    def __init__(self, name, doc=None, interface=None):
        self.name = name
        self.doc = doc
        self.interface = interface
        super(WSGIKey, self).__init__()

    def writeto(self, context):
        context.addindex('wsgikey', self.name)
        context.writekey(self.name, type='WSGI Environment Key')
        context.writedoc(self.doc)
        self.writeobj(self.interface, context)
        context.endkey()

class NoDefault: pass

class Config(DocItem):

    def __init__(self, doc, name=None, default=NoDefault):
        self.doc = doc
        self.name = name
        self.default = default

    def writeto(self, context):
        name = self.name
        if not self.name:
            name = context.last_name
            if name.startswith('_config_'):
                name = name[len('_config_'):]
        context.addindex('config', name)
        name = "``%s``" % name
        if self.default is not NoDefault:
            name += ' (default: ``%r``)' % self.default
        context.writekey(name, type='Paste Configuration',
                         monospace=False)
        context.writedoc(self.doc)
        context.endkey()

class Attribute(DocItem):

    def __init__(self, doc, name=None, interface=None):
        self.doc = doc
        self.name = name
        self.interface = interface
        super(Attribute, self).__init__()

    def writeto(self, context):
        name = self.name or context.last_name
        context.writekey(self.name, type='Attribute')
        context.writedoc(self.doc)
        if self.interface:
            context.write(self.interface)
        context.endkey()

def install():
    """
    Puts this module in place of the normal paste.docsupport.metadata
    module, which is all stubby because this functional module takes
    longer to import.
    """
    from paste.docsupport import metadata
    for name, value in globals().items():
        setattr(metadata, name, value)
    
