#!/usr/bin/env python

import optparse
import fnmatch
import os
import sys
from cStringIO import StringIO
import re
import textwrap
from paste.util.thirdparty import load_new_module
string = load_new_module('string', (2, 4))

from paste import pyconfig
from paste import urlparser
from paste import server
from paste import CONFIG
from paste.util import plugin

class InvalidCommand(Exception):
    pass

def find_template_info(args):
    """
    Given command-line arguments, this finds the app template
    (paste.app_templates.<template_name>.command).  It looks for a
    -t or --template option (but ignores all other options), and if
    none then looks in server.conf for a template_name option.

    Returns server_conf_fn, template_name, template_dir, module
    """
    template_name = None
    template_name, rest = find_template_option(args)
    server_conf_fn = None
    if template_name:
        next_template_name, rest = find_template_option(rest)
        if next_template_name:
            raise InvalidCommand(
                'You cannot give two templates on the commandline '
                '(first I found %r, then %r)'
                % (template_name, next_template_name))
    else:
        server_conf_fn, template_name = find_template_config(args)
    if not template_name:
        template_name = 'default'
    template_mod = plugin.load_plugin_module(
        'app_templates', 'paste.app_templates',
        template_name, '_tmpl')
    return (server_conf_fn, template_name,
            os.path.dirname(template_mod.__file__), template_mod)

def find_template_option(args):
    copy = args[:]
    while copy:
        if copy[0] == '--':
            return None, copy
        if copy[0] == '-t' or copy[0] == '--template':
            if not copy[1:] or copy[1].startswith('-'):
                raise InvalidCommand(
                    '%s needs to be followed with a template name' % copy[0])
            return copy[1], copy[2:]
        if copy[0].startswith('-t'):
            return copy[0][2:], copy[1:]
        if copy[0].startswith('--template='):
            return copy[0][len('--template='):], copy[1:]
        copy.pop(0)
    return None, []

def find_template_config(args):
    conf_fn = os.path.join(os.getcwd(), 'server.conf')
    if not os.path.exists(conf_fn):
        return None, None
    conf = pyconfig.Config(with_default=True)
    conf.load(conf_fn)
    return conf_fn, conf.get('app_template')

def run(args):
    try:
        server_conf_fn, name, dir, mod = find_template_info(args)
    except InvalidCommand, e:
        print str(e)
        return 2
    return mod.run(args, name, dir, mod, server_conf_fn)

class CommandRunner(object):

    def __init__(self):
        self.commands = {}
        self.command_aliases = {}
        self.register_standard_commands()
        self.server_conf_fn = None

    def run(self, argv, template_name, template_dir, template_module,
            server_conf_fn):
        self.server_conf_fn = server_conf_fn
        invoked_as = argv[0]
        args = argv[1:]
        for i in range(len(args)):
            if not args[i].startswith('-'):
                # this must be a command
                command = args[i].lower()
                del args[i]
                break
        else:
            # no command found
            self.invalid('No COMMAND given (try "%s help")'
                         % os.path.basename(invoked_as))
        real_command = self.command_aliases.get(command, command)
        if real_command not in self.commands.keys():
            self.invalid('COMMAND %s unknown' % command)
        runner = self.commands[real_command](
            invoked_as, command, args, self,
            template_name, template_dir, template_module)
        runner.run()

    def register(self, command):
        name = command.name
        self.commands[name] = command
        for alias in command.aliases:
            self.command_aliases[alias] = name

    def invalid(self, msg, code=2):
        print msg
        sys.exit(code)

    def register_standard_commands(self):
        # @@: these commands shouldn't require a template
        self.register(CommandHelp)
        self.register(CommandList)
        self.register(CommandServe)

############################################################
## Command framework
############################################################

def standard_parser(verbose=True, simulate=True, interactive=False):
    parser = optparse.OptionParser()
    if verbose:
        parser.add_option('-v', '--verbose',
                          help='Be verbose (multiple times for more verbosity)',
                          action='count',
                          dest='verbose',
                          default=0)
    if simulate:
        parser.add_option('-n', '--simulate',
                          help="Don't actually do anything (implies -v)",
                          action='store_true',
                          dest='simulate')
    if interactive:
        parser.add_option('-i', '--interactive',
                          help="Ask before doing anything (use twice to be more careful)",
                          action="count",
                          dest="interactive",
                          default=0)
    parser.add_option('-t', '--template',
                      help='Use this template',
                      metavar='NAME',
                      dest='template_name')
    return parser

class Command(object):

    min_args = 0
    min_args_error = 'You must provide at least %(min_args)s arguments'
    max_args = 0
    max_args_error = 'You must provide no more than %(max_args)s arguments'
    aliases = ()
    required_args = []
    description = None
    
    def __init__(self, invoked_as, command_name, args, runner,
                 template_name, template_dir, template_module):
        self.invoked_as = invoked_as
        self.command_name = command_name
        self.raw_args = args
        self.runner = runner
        self.template_name = template_name
        self.template_dir = template_dir
        self.template_module = template_module

    def run(self):
        self.parse_args(self.raw_args)
        if (getattr(self.options, 'simulate', False)
            and not self.options.verbose):
            self.options.verbose = 1
        if self.min_args is not None and len(self.args) < self.min_args:
            self.runner.invalid(
                self.min_args_error % {'min_args': self.min_args,
                                       'actual_args': len(self.args)})
        if self.max_args is not None and len(self.args) > self.max_args:
            self.runner.invalid(
                self.max_args_error % {'max_args': self.max_args,
                                       'actual_args': len(self.args)})
        for var_name, option_name in self.required_args:
            if not getattr(self.options, var_name, None):
                self.runner.invalid(
                    'You must provide the option %s' % option_name)
        self.command()

    def parse_args(self, args):
        self.parser.usage = "%%prog [options]\n%s" % self.summary
        self.parser.prog = '%s %s' % (
            os.path.basename(self.invoked_as),
            self.command_name)
        if self.description:
            self.parser.description = self.description
        self.options, self.args = self.parser.parse_args(args)

    def ask(self, prompt, safe=False, default=True):
        if self.options.interactive >= 2:
            default = safe
        if default:
            prompt += ' [Y/n]? '
        else:
            prompt += ' [y/N]? '
        while 1:
            response = raw_input(prompt).strip()
            if not response.strip():
                return default
            if response and response[0].lower() in ('y', 'n'):
                return response[0].lower() == 'y'
            print 'Y or N please'

    def _get_prog_name(self):
        return os.path.basename(self.invoked_as)
    prog_name = property(_get_prog_name)

############################################################
## Standard commands
############################################################
    
class CommandList(Command):

    name = 'list'
    summary = 'Show available templates'

    parser = standard_parser(simulate=False)

    max_args = 1

    def command(self):
        any = False
        app_template_dir = os.path.join(os.path.dirname(__file__), 'app_templates')
        for name in os.listdir(app_template_dir):
            dir = os.path.join(app_template_dir, name)
            if not os.path.exists(os.path.join(dir, 'description.txt')):
                if self.options.verbose >= 2:
                    print 'Skipping %s (no description.txt)' % dir
                continue
            if self.args and not fnmatch.fnmatch(name, self.args[0]):
                continue
            if not self.options.verbose:
                print '%s: %s\n' % (
                    name, self.template_description().splitlines()[0])
            else:
                return '%s: %s\n' % (
                    self.name, self.template_description())
            # @@: for verbosity >= 2 we should give lots of metadata
            any = True
        if not any:
            print 'No application templates found'

    def template_description(self):
        f = open(os.path.join(self.template_dir, 'description.txt'))
        content = f.read().strip()
        f.close()
        return content

class CommandServe(Command):

    name = 'serve'
    summary = 'Run server'
    parser = standard_parser(simulate=False)

    def command(self):
        sys.exit(server.run_commandline(self.args))

    def parse_args(self, args):
        # Unlike most commands, this takes arbitrary options and folds
        # them into the configuration
        conf, app = server.load_commandline(args)
        if conf is None:
            sys.exit(app)
        if app == 'help':
            self.help(conf)
            sys.exit()
        if conf.get('list_servers'):
            self.list_servers(conf)
            sys.exit()
        CONFIG.push_process_config(conf)
        sys.exit(server.run_server(conf, app))
        self.config = conf

    def help(self, config):
        # Here we make a fake parser just to get the help
        parser = optparse.OptionParser()
        group = parser.add_option_group("general options")
        group.add_options(server.load_commandline_options())
        extra_help = None
        if config.get('server'):
            try:
                server_mod = server.get_server_mod(config['server'])
            except plugin.PluginNotFound, e:
                print "Server %s not found" % config['server']
                print "  (%s)" % e
                sys.exit(1)
            ops = getattr(server_mod, 'options', None)
            if ops:
                group = parser.add_option_group(
                    "%s options" % server_mod.plugin_name,
                    description=getattr(server_mod, 'description', None))
                group.add_options(ops)
            extra_help = getattr(server_mod, 'help', None)
        parser.print_help()
        if extra_help:
            print
            # @@: textwrap kills any special formatting, so maybe
            # we just can't use it
            #print self.fill_text(extra_help)
            print extra_help

    def list_servers(self, config):
        server_ops = plugin.find_plugins('servers', '_server')
        server_ops.sort()
        print 'These servers are available:'
        print
        for server_name in server_ops:
            self.show_server(server_name)

    def show_server(self, server_name):
        server_mod = server.get_server_mod(server_name)
        print '%s:' % server_mod.plugin_name
        desc = getattr(server_mod, 'description', None)
        if not desc:
            print '    No description available'
        else:
            print self.fill_text(desc)

    def fill_text(self, text):
        try:
            width = int(os.environ['COLUMNS'])
        except (KeyError, ValueError):
            width = 80
        width -= 2
        return textwrap.fill(
            text,
            width,
            initial_indent=' '*4,
            subsequent_indent=' '*4)
        

class CommandHelp(Command):

    name = 'help'
    summary = 'Show help'

    parser = standard_parser(verbose=False)

    max_args = 1

    def command(self):
        if self.args:
            self.runner.run([self.invoked_as, self.args[0], '-h'],
                            self.template_name, self.template_dir,
                            self.template_module,
                            self.runner.server_conf_fn)
        else:
            print 'Available commands:'
            print '  (use "%s help COMMAND" or "%s COMMAND -h" ' % (
                self.prog_name, self.prog_name)
            print '  for more information)'
            items = self.runner.commands.items()
            items.sort()
            max_len = max([len(cn) for cn, c in items])
            for command_name, command in items:
                print '%s:%s %s' % (command_name,
                                    ' '*(max_len-len(command_name)),
                                    command.summary)
                if command.aliases:
                    print '%s (Aliases: %s)' % (
                        ' '*max_len, ', '.join(command.aliases))

############################################################
## Optional helper commands
############################################################

class CommandCreate(Command):

    name = 'create'
    summary = 'Create application from template'

    max_args = 1
    min_args = 1

    parser = standard_parser()

    default_options = {
        'server': 'wsgiutils',
        'verbose': True,
        'reload': True,
        'debug': True,
        }

    def command(self):
        self.output_dir = self.args[0]
        self.create(self.output_dir)
        if self.options.verbose:
            print 'Now do:'
            print '  cd %s' % self.options.output_dir
            print '  wsgi-server'

    def create(self, output_dir):
        file_dir = os.path.join(self.template_dir, 'template')
        if not os.path.exists(file_dir):
            raise OSError(
                'No %s directory, I don\'t know what to do next' % file_dir)
        template_options = self.default_options.copy()
        template_options.update(self.options.__dict__)
        template_options['app_name'] = os.path.basename(output_dir)
        template_options['base_dir'] = output_dir
        template_options['absolute_base_dir'] = os.path.abspath(output_dir)
        template_options['absolute_parent'] = os.path.dirname(
            os.path.abspath(output_dir))
        template_options['template_name'] = self.template_name
        self.copy_dir(file_dir, output_dir, template_options,
                      self.options.verbose, self.options.simulate)

    def copy_dir(self, *args, **kw):
        copy_dir(*args, **kw)

def copy_dir(source, dest, vars, verbosity, simulate):
    names = os.listdir(source)
    names.sort()
    if not os.path.exists(dest):
        if verbosity >= 1:
            print 'Creating %s/' % dest
        if not simulate:
            os.makedirs(dest)
    elif verbosity >= 2:
        print 'Directory %s exists' % dest
    for name in names:
        full = os.path.join(source, name)
        if name.startswith('.'):
            if verbosity >= 2:
                print 'Skipping hidden file %s' % full
            continue
        dest_full = os.path.join(dest, _substitute_filename(name, vars))
        if os.path.isdir(full):
            if verbosity:
                print 'Recursing into %s' % full
            copy_dir(full, dest_full, vars, verbosity, simulate)
            continue
        f = open(full, 'rb')
        content = f.read()
        f.close()
        content = _substitute_content(content, vars)
        if verbosity:
            print 'Copying %s to %s' % (full, dest_full)
        f = open(dest_full, 'wb')
        f.write(content)
        f.close()

def _substitute_filename(fn, vars):
    for var, value in vars.items():
        fn = fn.replace('+%s+' % var, str(value))
    return fn

def _substitute_content(content, vars):
    tmpl = string.Template(content)
    return tmpl.substitute(TypeMapper(vars))

class TypeMapper(dict):

    def __getitem__(self, item):
        if item.startswith('str_'):
            return repr(str(self[item[4:]]))
        elif item.startswith('bool_'):
            if self[item[5:]]:
                return 'True'
            else:
                return 'False'
        else:
            return dict.__getitem__(self, item)

if __name__ == '__main__':
    run(sys.argv)
