import inspect
import xmlrpclib
import traceback
from paste.httpexceptions import HTTPBadRequest
json = None

__all__ = ['unpack', 'unpack_xmlrpc', 'unpack_json']

def unpack(func):
    argspec = FunctionArgSpec(func)
    def replacement_func(self):
        args, kw = argspec.unpack_args(self.path_parts, self.fields)
        return func(self, *args, **kw)
    replacement_func.__doc__ = func.__doc__
    replacement_func.__name__ = func.__name__
    return replacement_func

def unpack_xmlrpc(func):
    def replacement_func(self):
        assert self.environ['CONTENT_TYPE'].startswith('text/xml')
        data = self.environ['wsgi.input'].read()
        xmlargs, method_name = xmlrpclib.loads(data)
        if method_name:
            kw = {'method_name': method_name}
        else:
            kw = {}
        self.set_header('content-type', 'text/xml; charset=UTF-8')
        try:
            result = func(self, *xmlargs, **kw)
        except:
            body = make_rpc_exception(environ, sys.exc_info())
            body = xmlrpclib.dumps(
                xmlrpclib.Fault(1, fault), encoding='utf-8')
        else:
            if not isinstance(result, tuple):
                result = (result,)
            body = xmlrpclib.dumps(
                result, methodresponse=True, encoding='utf-8')
        self.write(body)
    replacement_func.__doc__ = func.__doc__
    replacement_func.__name__ = func.__name__
    return replacement_func

def make_rpc_exception(environ, exc_info):
    config = environ['paste.config']
    rpc_exception = config.get('rpc_exception', None)
    if rpc_exception not in (None, 'occurred', 'exception', 'traceback'):
        environ['wsgi.errors'].write(
            "Bad 'rpc_exception' setting: %r\n" % rpc_exception)
        rpc_exception = None
    if rpc_exception is None:
        if config.get('debug'):
            rpc_exception = 'traceback'
        else:
            rpc_exception = 'exception'
    if rpc_exception == 'occurred':
        fault = 'unhandled exception'
    elif rpc_exception == 'exception':
        fault = str(e)
    elif rpc_exception == 'traceback':
        out = StringIO()
        traceback.print_exception(*exc_info, **{'file': out})
        fault = out.getvalue()
    return fault

def unpack_json(func):
    global json
    if json is None:
        import json
    def replacement_func(self):
        data = self.environ['wsgi.input'].read()
        jsonrpc = json.jsonToObj(data)
        method = jsonrpc['method']
        params = jsonrpc['params']
        id = jsonrpc['id']
        if method:
            kw = {'method_name': method}
        else:
            kw = {}
        self.set_header('content-type', 'text/plain; charset: UTF-8')
        try:
            result = func(self, *params, **kw)
        except:
            body = make_rpc_exception(environ, sys.exc_info())
            response = {
                'result': None,
                'error': body,
                'id': id}
        else:
            response = {
                'result': result,
                'error': None,
                'id': id}
        self.write(json.objToJson(response))
    replacement_func.__doc__ = func.__doc__
    replacement_func.__name__ = func.__name__
    return replacement_func


class FunctionArgSpec(object):

    def __init__(self, func):
        self.funcargs, self.varargs, self.varkw, self.defaults = (
            inspect.getargspec(func))
        self.positional = []
        self.optional_pos = []
        self.coersions = self.collect_coersions(self.funcargs)
        while self.funcargs and self.funcargs[0].endswith('_path'):
            if len(self.defaults or ()) == len(self.funcargs):
                # This is an optional path segment
                self.optional_pos.append(self.funcargs.pop(0))
                self.defaults = self.defaults[1:]
            else:
                self.positional.append(self.funcargs.pop(0))
        self.reqargs = []
        if not self.defaults:
            self.reqargs = self.funcargs
        else:
            self.reqargs = self.funcargs[:-len(self.defaults)]

    def unpack_args(self, path_parts, fields):
        args = []
        kw = {}
        if len(self.positional) > len(path_parts):
            raise HTTPBadRequest(
                "Not enough parameters on the URL (expected %i more "
                "path segments)" % (len(self.positional)-len(path_parts)))
        if (not self.varargs
            and (len(self.positional)+len(self.optional_pos))
                 < len(path_parts)):
            raise HTTPBadRequest(
                "Too many parameters on the URL (expected %i less path "
                "segments)" % (len(path_parts)-len(self.positional)
                               -len(self.optional_pos)))
        for name, value in fields.iteritems():
            if not self.varkw and name not in self.coersions:
                raise HTTPBadRequest(
                    "Variable %r not expected" % name)
            if name not in self.coersions:
                kw[name] = value
                continue
            orig_name, coercer = self.coersions[name]
            if coercer:
                try:
                    value = coercer(value)
                except (ValueError, TypeError), e:
                    raise HTTPBadRequest(
                        "Bad variable %r: %s" % (name, e))
            kw[orig_name] = value
        for arg in self.reqargs:
            if arg not in kw:
                raise HTTPBadRequest(
                    "Variable %r required" % arg)
        return args, kw
            
    def collect_coersions(self, funcargs):
        coersions = {}
        for name in funcargs:
            coercer = normal
            orig = name
            while 1:
                if name.endswith('_int'):
                    coercer = self.add_coercer(coercer, make_int)
                    name = name[:-4]
                elif name.endswith('_list'):
                    coercer = self.add_coercer(coercer, make_list)
                    name = name[:-5]
                elif name.endswith('_float'):
                    coercer = self.add_coercer(coercer, make_float)
                    name = name[:-6]
                elif name.endswith('_req'):
                    coercer = self.add_coercer(coercer, make_required)
                    name = name[:-4]
                else:
                    break
            coersions[name] = (orig, coercer)
        return coersions

    def add_coercer(self, coercer, new_coercer):
        if not coercer or coercer is normal:
            return new_coercer
        else:
            def coerce(val):
                return new_coercer(coercer(val))
            return coerce

def make_int(v):
    if isinstance(v, list):
        return map(int, v)
    else:
        return int(v)

def make_float(v):
    if isinstance(v, list):
        return map(float, v)
    else:
        return float(v)

def make_list(v):
    if isinstance(v, list):
        return v
    else:
        return [v]

def make_required(s):
    if s is None:
        raise TypeError
    return s

def normal(v):
    if isinstance(v, list):
        raise ValueError("List not expected")
    return v
