from console.sitepage import SitePage
from console.JSONComponent import JSONComponent
from console.evalcontext import EvalContext

context = EvalContext()

class index(SitePage):

    components = SitePage.components + [
        JSONComponent(baseConfig='console')]

    def setup(self):
        self.options.title = 'Console'
        
    def jsonMethods(self):
        return ['run']
    
    def run(self, expr):
        if not expr.endswith('\n'):
            expr += '\n'
        return context.exec_expr(expr)
