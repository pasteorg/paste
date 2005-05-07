from cStringIO import StringIO
import traceback
import pdb
import threading
import sys
from console.sitepage import SitePage
from console.JSONComponent import JSONComponent

global_namespace = {}
namespace_lock = threading.Lock()

# From doctest
class _OutputRedirectingPdb(pdb.Pdb):
    """
    A specialized version of the python debugger that redirects stdout
    to a given stream when interacting with the user.  Stdout is *not*
    redirected when traced code is executed.
    """
    def __init__(self, out):
        self.__out = out
        pdb.Pdb.__init__(self)

    def trace_dispatch(self, *args):
        # Redirect stdout to the given stream.
        save_stdout = sys.stdout
        sys.stdout = self.__out
        # Call Pdb's trace dispatch method.
        try:
            return pdb.Pdb.trace_dispatch(self, *args)
        finally:
            sys.stdout = save_stdout

class index(SitePage):

    components = SitePage.components + [
        JSONComponent(baseConfig='console')]

    def setup(self):
        self.options.title = 'Console'
        
    def jsonMethods(self):
        return ['run']
    
    def run(self, value):
        out = StringIO()
        namespace_lock.acquire()
        save_stdout = sys.stdout
        try:
            debugger = _OutputRedirectingPdb(save_stdout)
            debugger.reset()
            pdb.set_trace = debugger.set_trace
            sys.stdout = out
            try:
                code = compile(value, '<web>', "single", 0, 1)
                exec code in global_namespace
                debugger.set_continue()
            except KeyboardInterrupt:
                raise
            except:
                traceback.print_exc(file=out)
                debugger.set_continue()
        finally:
            sys.stdout = save_stdout
            namespace_lock.release()
        value = out.getvalue()
        return value
