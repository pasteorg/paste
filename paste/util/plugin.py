import os
import import_string

paste_dir = os.path.dirname(os.path.dirname(__file__))

def find_plugins(dir):
    """
    Looks in directory for plugins, and returns them by name.
    A plugin can be a .txt file, .py file, or directory.
    """
    plugins = []
    dir = os.path.join(paste_dir, dir))
    for name in os.listdir(dir):
        if os.path.isdir(os.path.join(dir, name)):
            plugins.append(name)
        ext = os.path.splitext(name)[1].lower()
        if name in ('.py', '.txt'):
            plugins.append(name)
    return plugins

def load_plugin_module(dir, dir_package, name):
    """
    Loads a plugin module.  Either the module is imported, or if it
    is a .txt file then the file is loaded and must contain the name
    of another module to be loaded (empty and comment lines ignored).

    dir_package is the package name of the directory.  Dotted names
    are not supported.
    """
    dir = os.path.join(paste_dir, dir)
    if os.path.exists(os.path.join(dir, name + '.txt')):
        module_name = parse_txt_plugin(os.path.join(dir, name + '.txt'))
    else:
        module_name = dir_package + '.' + name
    return import_string.import_module(module_name)

def parse_txt_plugin(fn):
    f = open(fn)
    try:
        module_name = None
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if module_name is not None:
                raise ValueError(
                    "Plugin file %s contains more than one line that "
                    "could be interpreted as a module name" % fn)
        if module_name is None:
            raise ValueError(
                "Plugin file %s does not contain a module name" % fn)
        return module_name
    finally:
        f.close()
