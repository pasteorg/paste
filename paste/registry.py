"""Registry for Stacked

The Registry is intended to ensure that thread-local objects which are
stacked are popped and pushed properly when a request is started and
finished.

Thread-locals capable of being stacked are registered with the middleware
and then tracked to ensure they're popped.

To ease creation of stacked thread-locals, an object with this interface
is supplied.

A stacked thread-local implements both thread-local access, and internally
tracks the objects in a stack. The thread-local has objects pushed and
popped from the stack to ensure that the correct object is being accessed
for the scope of the request. 

For convenience, the stacked thread-local can be used exactly like the
object its tracking and will proxy all access through to the current
object.

An ideal use is for making request-specific objects available in a global
manner while ensuring that when the object is accessed, the correct one is
being used.

Example::
    
    #somemodule.py
    myvar = StackedObjectProxy()
    
    #wsgi app stack
    from paste.registry import RegistryManager
    
    app = RegistryManager(app)
    
    #inside your wsgi app
    class yourapp(object):
        def __call__(self, environ, start_response):
            obj = someobject  # Your object
            if environ.has_key('paste.registry'):
                environ['paste.registry'].register(somemodule.myvar, obj)

You will then be able to import somemodule anywhere in your WSGI app or in
the calling stack below it and be assured that it is using the object you
registered with Registry.

"""
import paste.util.threadinglocal as threadinglocal
from paste import wsgilib

__all__ = ['StackedObjectProxy', 'RegistryManager']

class StackedObjectProxy(object):
    """Track an object instance internally using a stack
    
    The StackedObjectProxy proxies access to an object internally using a
    stacked thread-local. This makes it safe for complex WSGI environments
    where access to the object may be desired in multiple places without
    having to pass the actual object around.
    
    New objects are added to the top of the stack with push_thread_object
    while objects can be removed with pop_thread_object. 
    
    """
    def __init__(self):
        self.__dict__['local'] = threadinglocal.local()
        
    def current_obj(self):
        objects = getattr(self.__dict__['local'], 'objects', None)
        if objects:
            return objects[-1]
        else:
            raise TypeError(
                "No object has been registered for this thread")
    
    def __getattr__(self, attr):
        return getattr(self.current_obj(), attr)
    
    def __setattr__(self, attr, value):
        setattr(self.current_obj(), name, value)
        
    def __delattr__(self, name):
        self.current_obj().__delattr__(name)
    
    def __getitem__(self, key):
        return self.current_obj()[key]
    
    def __setitem__(self, key, value):
        self.current_obj()[key] = value

    def __delitem__(self, key):
        self.current_obj().__delitem__(key)
    
    def __repr__(self):
        return self.current_obj().__repr__()
    
    def __iter__(self):
        """Only works for proxying to a dict"""
        return iter(self.current_obj().keys())
    
    def __contains__(self, key):
        # I thought __getattr__ would catch this, but apparently not
        return self.current_obj().has_key(key)
    
    def push_object(self, obj):
        """Make ``obj`` the active object for this thread.
        
        This should be used like::

            obj = yourobject()
            module.glob = StackedObjectProxy()
            module.glob.push_object(obj)
            try:
                ... do stuff ...
            finally:
                module.glob.pop_object(conf)
        
        """
        if not hasattr(self.local, 'objects'):
            self.local.objects = []
        self.local.objects.append(obj)
    
    def pop_object(self, obj=None):
        """Remove a thread-local object.
        
        If ``obj`` is given, it is checked against the popped object and an
        error is emitted if they don't match.
        """
        if not hasattr(self.local, 'objects'):
            raise AssertionError("No object has been registered for this thread.")
        popped = self.local.objects.pop()
        if obj:
            if popped is not obj:
                raise AssertionError(
                    "The object popped (%s) is not the same as the object "
                    "expected (%s)"
                    % (popped, obj))

class Registry(object):
    """Track objects and stacked object proxies for removal"""
    def __init__(self):
        self.reglist = []
    
    def prepare(self):
        """Anytime a new RegistryManager comes in, it needs to add
        objects for tracking using 
        """
        self.reglist.append({})
    
    def register(self, stacked, obj):
        stacked.push_object(obj)
        myreglist = self.reglist[-1]
        myreglist[id(stacked)] = (stacked, obj)
    
    def cleanup(self):
        for id, val in self.reglist[-1].iteritems():
            stacked, obj = val
            stacked.pop_object(obj)
        self.reglist.pop()
    
class IterWrap(object):
    def __init__(self, iter, close_func):
        self.iter = iter
        self.close_func = close_func
    
    def __iter__(self):
        return self
    
    def next(self):
        try:
            return self.iter.next()
        except StopIteration:
            self.close_func()
            raise StopIteration
    
class RegistryManager(object):
    def __init__(self, application):
        self.application = application
        
    def __call__(self, environ, start_response):
        app_iter = None
        reg = environ.setdefault('paste.registry', Registry())
        reg.prepare()
        try:
            app_iter = self.application(environ, start_response)
        finally:
            if app_iter is None:
                # An error occurred...
                reg.cleanup()
        if type(app_iter) in (list, tuple):
            # Because it is a concrete iterator (not a generator) we
            # know the configuration for this thread is no longer
            # needed:
            reg.cleanup()
            return app_iter
        else:
            new_app_iter = iter(IterWrap(app_iter, reg.cleanup))
            return new_app_iter


