This directory contains plugins for servers.  Each plugin is
identified by having "_server" on the end of its name.  Plugins can be
directories (Python packages), Python modules, or text (.txt) files.

A text file must contain one (non-empty, non-comment) line, which is
the name of a module that should be considered a server.  E.g., you'd
put "myapp.my_paste_server" in there, so that you could implement a
server in your own package.

Modules should have certain symbols (only 'serve' is required):

serve(conf, app):
    Required; this serves the given application, using the given
    configuration options.
options:
    A list of (option_name, option_help), describing the options this
    servers uses.
description:
    A fairly short (2-3 line) description of this server.
help:
    A longer help text.

Note: if you have a package, __init__.py must contain these
variables. 