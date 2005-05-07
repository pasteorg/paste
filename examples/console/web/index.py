from console.sitepage import SitePage
from console.JSONComponent import JSONComponent
from console.evalcontext import EvalContext
import time

context = EvalContext()

class index(SitePage):

    components = SitePage.components + [
        JSONComponent(baseConfig='console')]

    def awake(self, trans):
        self.t1 = time.time()
        SitePage.awake(self, trans)

    def setup(self):
        self.options.title = 'Console'
        
    def jsonMethods(self):
        return ['run']

    def actions(self):
        return ['postrun']
    
    def run(self, expr):
        self.t2 = time.time()
        if not expr.endswith('\n'):
            expr += '\n'
        result = context.exec_expr(expr)
        self.t3 = time.time()
        timing = '%s - %s\n%s' % (
            self.t2 - self.t1, self.t3 - self.t2, result)
        return timing

    def postrun(self):
        self.response().setHeader('content-type', 'text/plain')
        expr = self.request().field('command', '')
        if not expr.endswith('\n'):
            expr += '\n'
        result = context.exec_expr(expr)
        print [expr, result]
        self.write(result)
    
