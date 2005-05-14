import os
import sys
from paste import server

def serve(conf, app):
    replacements = {}
    replacements['default_config_fn'] = os.path.abspath(
        server.default_config_fn)

    # Ideally, other_conf should be any options that came from the
    # command-line.
    # @@: This assumes too much about the ordering of namespaces.
    other_conf = dict(conf.namespaces[-2])
    # Not a good idea to let 'verbose' through, but this doesn't really
    # stop any sourced configs from setting it either...
    if other_conf.has_key('verbose'):
        del other_conf['verbose']
    replacements['other_conf'] = other_conf

    template_fn = os.path.join(os.path.dirname(__file__),
                               'server_script_template.py')
    template = open(template_fn).read()
    for name, value in replacements.items():
        template = template.replace('@@' + name + '@@', repr(value))

    print "#!%s" % sys.executable
    print template
    print "if __name__ == '__main__':"
    print "    from paste.cgiserver import run_with_cgi"
    print "    run_with_cgi(app)"
