from paste.util.classinit import ClassInitMeta

handler_exts = {}

def get_handler(path):
    if path.check(dir=True):
        ext_type = 'dir'
    else:
        ext_type = path.ext
    return handler_exts.get(ext, handler_exts['*'])(path)

class Handler(object):
    
    __metaclass__ = ClassInitMeta

    abstract = True
    exts = ()

    def __classinit__(cls, new_args):
        if cls.abstract and 'abstract' not in new_args:
            cls.abstract = False
        if not cls.abstract:
            for ext in self.exts:
                assert ext not in handler_exts, (
                    "Handler %s already registered for extension %r; "
                    "trying to overwrite with %s"
                    % (handler_exts[ext], ext, cls))
                handler_exts[ext] = cls

    def __init__(self, path):
        self.path = path
        
