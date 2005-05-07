from console.sitepage import SitePage
from console.JSONComponent import JSONComponent
from console.evalcontext import EvalContext
import time

context = EvalContext()

class index(SitePage):

    components = SitePage.components + [
        JSONComponent(baseConfig='console')]

    def awake(self, trans):
        SitePage.awake(self, trans)

    def setup(self):
        self.options.title = 'Console'
        
    def jsonMethods(self):
        return ['run']

    def actions(self):
        return ['postrun']
    
    def run(self, expr):
        # jsonrpc isn't currently used
        if not expr.endswith('\n'):
            expr += '\n'
        result = context.exec_expr(expr)
        return result

    def postrun(self):
        self.response().setHeader('content-type', 'text/plain')
        expr = self.request().field('command', '')
        if not expr.endswith('\n'):
            expr += '\n'
        result = context.exec_expr(expr)
        self.write(result)
    
