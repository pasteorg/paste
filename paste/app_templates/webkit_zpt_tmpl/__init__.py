import os
from paste import app_setup
from paste import pyconfig

the_runner = app_setup.CommandRunner()
the_runner.register(app_setup.CommandCreate)

class CommandServlet(app_setup.Command):

    name = 'servlet'
    summary = 'Create a new servlet and template'
    max_args = 1
    min_args = 1

    parser = app_setup.standard_parser()

    def command(self):
        servlet_fn = os.path.splitext(self.args[0])[0]
        config = {}
        if '/' in servlet_fn or '\\' in servlet_fn:
            servlet_name = os.path.basename(servlet_fn)
        else:
            servlet_name = servlet_fn
        if self.runner.server_conf_fn:
            config = pyconfig.Config(with_default=True)
            config.load(self.runner.server_conf_fn)
            output_dir = config.get('base_dir')
            if output_dir is None:
                output_dir = os.path.dirname(self.runner.server_conf_fn)
        else:
            output_dir = os.getcwd()
        source_dir = os.path.join(self.template_dir, 'servlet_template')
        template_options = config.copy()
        template_options.update(self.options.__dict__)
        template_options.update({
            'servlet_name': servlet_name,
            'servlet_fn': servlet_fn,
            })
        app_setup.copy_dir(
            source_dir, output_dir, template_options,
            self.options.verbose, self.options.simulate)

the_runner.register(CommandServlet)

run = the_runner.run
