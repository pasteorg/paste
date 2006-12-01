# (c) 2005 Ben Bangert
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Registry for handling request-local module globals sanely

Dealing with module globals in a thread-safe way is good if your
application is the sole responder in a thread, however that approach fails
to properly account for various scenarios that occur with WSGI applications
and middleware.

What is actually needed in the case where a module global is desired that
is always set properly depending on the current request, is a stacked
thread-local object. Such an object is popped or pushed during the request
cycle so that it properly represents the object that should be active for
the current request.

To make it easy to deal with such variables, this module provides a special
StackedObjectProxy class which you can instantiate and attach to your
module where you'd like others to access it. The object you'd like this to
actually "be" during the request is then registered with the
RegistryManager middleware, which ensures that for the scope of the current
WSGI application everything will work properly.

Example:

.. code-block:: Python
    
    #yourpackage/__init__.py
    
    from paste.registry import RegistryManager, StackedObjectProxy
    myglobal = StackedObjectProxy()
    
    #wsgi app stack
    app = RegistryManager(yourapp)
    
    #inside your wsgi app
    class yourapp(object):
        def __call__(self, environ, start_response):
            obj = someobject  # The request-local object you want to access
                              # via yourpackage.myglobal
            if environ.has_key('paste.registry'):
                environ['paste.registry'].register(myglobal, obj)

You will then be able to import yourpackage anywhere in your WSGI app or in
the calling stack below it and be assured that it is using the object you
registered with Registry.

RegisterManager can be in the WSGI stack multiple times, each time it
appears it registers a new request context.


Performance
===========

The overhead of the proxy object is very minimal, however if you are using
proxy objects extensively (Thousands of accesses per request or more), there
are some ways to avoid them. A proxy object runs approximately 3-20x slower
than direct access to the object, this is rarely your performance bottleneck
when developing web applications.

Should you be developing a system which may be accessing the proxy object
thousands of times per request, the performance of the proxy will start to
become more noticeabe. In that circumstance, the problem can be avoided by
getting at the actual object via the proxy with the ``_curent_obj`` function:

.. code-block:: Python
    
    #sessions.py
    Session = StackedObjectProxy()
    # ... initialization code, etc.
    
    # somemodule.py
    import sessions
    
    def somefunc():
        session = sessions.Session._current_obj()
        # ... tons of session access

This way the proxy is used only once to retrieve the object for the current
context and the overhead is minimized while still making it easy to access
the underlying object. The ``_current_obj`` function is preceded by an
underscore to more likely avoid clashing with the contained object's
attributes.

**NOTE:** This is *highly* unlikely to be an issue in the vast majority of
cases, and requires incredibly large amounts of proxy object access before
one should consider the proxy object to be causing slow-downs. This section
is provided solely in the extremely rare case that it is an issue so that a
quick way to work around it is documented.

"""
import new
import sys
import warnings
import paste.util.threadinglocal as threadinglocal

__all__ = ['StackedObjectProxy', 'RegistryManager']

class StackedObjectProxy(object):
    """Track an object instance internally using a stack
    
    The StackedObjectProxy proxies access to an object internally using a
    stacked thread-local. This makes it safe for complex WSGI environments
    where access to the object may be desired in multiple places without
    having to pass the actual object around.
    
    New objects are added to the top of the stack with push_object while
    objects can be removed with pop_object. 
    
    """
    def __init__(self, default=None, name="Default"):
        """Create a new StackedObjectProxy
        
        If a default is given, its used in every thread if no other object
        has been pushed on.
        
        """
        self.__dict__['_name'] = name
        self.__dict__['local'] = threadinglocal.local()
        if default:
            self.__dict__['_default_object'] = default
    
    def __getattr__(self, attr):
        return getattr(self._current_obj(), attr)
    
    def __setattr__(self, attr, value):
        setattr(self._current_obj(), attr, value)
    
    def __delattr__(self, name):
        self._current_obj().__delattr__(name)
    
    def __getitem__(self, key):
        return self._current_obj()[key]
    
    def __setitem__(self, key, value):
        self._current_obj()[key] = value
    
    def __delitem__(self, key):
        self._current_obj().__delitem__(key)
    
    def __repr__(self):
        try:
            return repr(self._current_obj())
        except TypeError:
            return '<%s.%s object at 0x%08x>' % (__name__,
                                                   self.__class__.__name__,
                                                   id(self))
    
    def __iter__(self):
        """Only works for proxying to a dict"""
        return iter(self._current_obj().keys())
    
    def __len__(self):
        return len(self._current_obj())
    
    def __contains__(self, key):
        return self._current_obj().has_key(key)
    
    def current_obj(self):
        """
        Deprecated (Aug 15 2006); moved to _current_obj.
        """
        warnings.warn('StackedObjectProxy.current_obj has been moved to '
                      'StackedObjectProxy._current_obj', DeprecationWarning, 2)
        return self._current_obj()

    def _current_obj(self):
        """Returns the current active object being proxied to
        
        In the event that no object was pushed, the default object if
        provided will be used. Otherwise, a TypeError will be raised.
        
        """
        objects = getattr(self.__dict__['local'], 'objects', None)
        if objects:
            return objects[-1]
        else:
            object = self.__dict__.get('_default_object')
            if object:
                return object
            else:
                raise TypeError(
                    'No object (name: %s) has been registered for this '
                    'thread' % self.__dict__['_name'])

    def push_object(self, obj):
        """
        Deprecated (Aug 15 2006); moved to _push_object.
        """
        warnings.warn('StackedObjectProxy.push_object has been moved to '
                      'StackedObjectProxy._push_object', DeprecationWarning, 2)
        self._push_object(obj)

    def _push_object(self, obj):
        """Make ``obj`` the active object for this thread-local.
        
        This should be used like:
        
        .. code-block:: Python

            obj = yourobject()
            module.glob = StackedObjectProxy()
            module.glob._push_object(obj)
            try:
                ... do stuff ...
            finally:
                module.glob._pop_object(conf)
        
        """
        if not hasattr(self.local, 'objects'):
            self.local.objects = []
        self.local.objects.append(obj)
    
    def pop_object(self, obj=None):
        """
        Deprecated (Aug 15 2006); moved to _pop_object.
        """
        warnings.warn('StackedObjectProxy.pop_object has been moved to '
                      'StackedObjectProxy._pop_object', DeprecationWarning, 2)
        self._pop_object(obj)

    def _pop_object(self, obj=None):
        """Remove a thread-local object.
        
        If ``obj`` is given, it is checked against the popped object and an
        error is emitted if they don't match.
        
        """
        if not hasattr(self.local, 'objects'):
            raise AssertionError('No object has been registered for this thread')
        popped = self.local.objects.pop()
        if obj:
            if popped is not obj:
                raise AssertionError(
                    'The object popped (%s) is not the same as the object '
                    'expected (%s)' % (popped, obj))

class Registry(object):
    """Track objects and stacked object proxies for removal
    
    The Registry object is instantiated a single time for the rquest no
    matter how many times the RegistryManager is used in a WSGI stack. Each
    RegistryManager must call ``prepare`` before continuing the call to
    start a new context for object registering.
    
    Each context is tracked with a dict inside a list. The last list
    element is the currently executing context. Each context dict is keyed
    by the id of the StackedObjectProxy instance being proxied, the value
    is a tuple of the StackedObjectProxy instance and the object being
    tracked.
    
    """
    def __init__(self):
        """Create a new Registry object
        
        ``prepare`` must still be called before this Registry object can be
        used to register objects.
        
        """
        self.reglist = []
    
    def prepare(self):
        """Used to create a new registry context
        
        Anytime a new RegistryManager is called, ``prepare`` needs to be
        called on the existing Registry object. This sets up a new context
        for registering objects.
        
        """
        self.reglist.append({})
    
    def register(self, stacked, obj):
        """Register an object with a StackedObjectProxy"""
        stacked._push_object(obj)
        myreglist = self.reglist[-1]
        myreglist[id(stacked)] = (stacked, obj)
    
    def cleanup(self):
        """Remove all objects from all StackedObjectProxy instances that
        were tracked at this Registry context"""
        for id, val in self.reglist[-1].iteritems():
            stacked, obj = val
            stacked._pop_object(obj)
        self.reglist.pop()
        
class RegistryManager(object):
    """Creates and maintains a Registry context
    
    RegistryManager creates a new registry context for the registration of
    StackedObjectProxy instances. Multiple RegistryManager's can be in a
    WSGI stack and will manage the context so that the StackedObjectProxies
    always proxy to the proper object.
    
    The object being registered can be any object sub-class, list, or dict.
    
    Registering objects is done inside a WSGI application under the
    RegistryManager instance, using the ``environ['paste.registry']``
    object which is a Registry instance.
        
    """
    def __init__(self, application):
        self.application = application
        
    def __call__(self, environ, start_response):
        app_iter = None
        reg = environ.setdefault('paste.registry', Registry())
        reg.prepare()
        try:
            app_iter = self.application(environ, start_response)
        except Exception, e:
            # Regardless of if the content is an iterable, generator, list
            # or tuple, we clean-up right now. If its an iterable/generator
            # care should be used to ensure the generator has its own ref
            # to the actual object
            if environ.get('paste.evalexception'):
                # EvalException is present in the WSGI stack
                expected = False
                for expect in environ.get('paste.expected_exceptions', []):
                    if isinstance(e, expect):
                        expected = True
                if not expected:
                    # An unexpected exception: save state for EvalException
                    restorer.save_registry_state(environ)
            reg.cleanup()
            raise
        except:
            # Save state for EvalException if it's present
            if environ.get('paste.evalexception'):
                restorer.save_registry_state(environ)
            reg.cleanup()
            raise
        else:
            reg.cleanup()
        
        return app_iter

class StackedObjectRestorer(object):
    """Track StackedObjectProxies and their proxied objects for automatic
    restoration within EvalException's interactive debugger.

    This singleton tracks all StackedObjectProxy state in existence when
    unexpected exceptions are raised by WSGI applications housed by
    EvalException and RegistryManager. Like EvalException, this information is
    stored for the life of the process.

    When an unexpected exception occurs and EvalException is enabled,
    save_registry_state is intended to be called to store the Registry state
    and enable automatic restoration on all currently registered
    StackedObjectProxies.

    With restoration enabled, those StackedObjectProxies' _current_obj
    (overwritten by _current_obj_evalexception) method's strategy is changed to
    determine whether or not an EvalException EvalContext is currently
    executing in the current thread. If so, it returns the appropriate proxied
    object from the restorer. If EvalException isn't running the
    StackedObjectProxy acts as it normally would (with the added performance
    hit).

    The overhead of enabling restoration is negligible (another threadlocal
    access) but worth mentioning when combined with StackedObjectProxy's normal
    overhead. Once enabled it does not turn off, however:

    o Enabling restoration only occurs after an unexpected exception is
    detected. The server is likely to be restarted shortly after the exception
    is raised to fix the cause

    o StackedObjectRestorer is only enabled when EvalException is enabled (not
    on a production server) and RegistryManager exists in the middleware
    stack"""
    def __init__(self):
        # Registry reglists by request_id
        self.saved_registry_states = {}
        self.evalcontext_id = threadinglocal.local()

    def save_registry_state(self, environ):
        """Save the current state (top of the stack) of the registry to the
        saved_registry_states dict, keyed by the request's unique identifier"""
        registry = environ.get('paste.registry')
        if not registry:
            return
        if not len(registry.reglist):
            # No state to save
            return

        # The current level of the stack to be saved
        saved_reglist = registry.reglist[-1]
        for stacked, obj in saved_reglist.itervalues():
            # Tweak the StackedObjectProxies we want to save state for --
            # change the _current_obj stategy to search for the original
            # proxied object when ran from EvalException
            if '_current_obj' not in stacked.__dict__:
                self.enable_restoration(stacked)

        # prepend instead of append: we're gathering the Registry stack in the
        # opposite direction
        self.saved_registry_states.setdefault(get_request_id(environ),
                                              []).insert(0, saved_reglist)

    def get_saved_proxied_obj(self, stacked, request_id):
        """Retrieve the saved object proxied by the specified
        StackedObjectProxy for the request identified by request_id"""
        # All state for the request identifed by request_id
        reglists = self.saved_registry_states[request_id]
        # The top of the stack was current when the exception occurred
        top_reglist = reglists[-1]
        return top_reglist[id(stacked)][1]

    def enable_restoration(self, stacked):
        """Replace the specified StackedObjectProxy's _current_obj method with
        _current_obj_evalexception: forces recovery of the saved proxied object
        during EvalException's EvalContext call"""
        orig_current_obj = stacked._current_obj
        def _current_obj_evalexception(self):
            request_id = restorer.in_evalcontext()
            if request_id:
                return restorer.get_saved_proxied_obj(self, request_id)
            return orig_current_obj()

        orig_doc = str(orig_current_obj.__doc__).strip()
        doc = ('%s\n(Automatic restoration of proxied objects for '
               'EvalException is enabled)' % orig_doc)
        _current_obj_evalexception.__doc__ = doc
        bound_wrapper = new.instancemethod(_current_obj_evalexception, stacked,
                                           stacked.__class__)
        stacked.__dict__['_current_obj'] = bound_wrapper

    def evalcontext_begin(self, request_id):
        """Register an EvalException EvalContext as being ran in the current
        thread for the specified request_id"""
        self.evalcontext_id.request_id = request_id

    def evalcontext_end(self):
        """Register an EvalException EvalContext as finished executing, if one
        exists"""
        try:
            del self.evalcontext_id.request_id
        except AttributeError:
            pass

    def in_evalcontext(self):
        """Determine if an EvalException EvalContext is currently running.
        Returns the request_id it's running for if so, otherwise False"""
        return getattr(self.evalcontext_id, 'request_id', False)

restorer = StackedObjectRestorer()

def get_request_id(environ):
    """Return a uniqe identifier for the current request"""
    from paste.evalexception.middleware import get_debug_count
    return get_debug_count(environ)
