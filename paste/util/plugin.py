import os
import import_string

class PluginNotFound(ImportError):
    pass

paste_dir = os.path.dirname(os.path.dirname(__file__))

def find_plugins(dir, name_extension=''):
    """
    Looks in directory for plugins, and returns them by name.
    A plugin can be a .txt file, .py file, or directory.

    If name_extension is given, only files ending with that string
    will be found (and that string will be removed).
    """
    plugins = []
    dir = os.path.join(paste_dir, dir)
    for name in os.listdir(dir):
        if name.startswith('.'):
            continue
        if not os.path.splitext(name)[0].endswith(name_extension):
            continue
        if os.path.isdir(os.path.join(dir, name)):
            if name_extension:
                plugins.append(name[:-len(name_extension)])
            else:
                plugins.append(name)
            continue
        base, ext = os.path.splitext(name)
        if ext.lower() in ('.py', '.txt'):
            if name_extension:
                plugins.append(base[:-len(name_extension)])
            else:
                plugins.append(base)
    return plugins

def load_plugin_module(dir, dir_package, name, name_extension=''):
    """
    Loads a plugin module.  Either the module is imported, or if it
    is a .txt file then the file is loaded and must contain the name
    of another module to be loaded (empty and comment lines ignored).

    dir_package is the package name of the directory.  Dotted names
    are not supported.
    """
    dir = os.path.join(paste_dir, dir)
    txt_name = name + name_extension + '.txt'
    if os.path.exists(os.path.join(dir, txt_name)):
        module_name = parse_txt_plugin(os.path.join(dir, txt_name))
    else:
        module_name = dir_package + '.' + name + name_extension
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
                raise PluginNotFound(
                    "Plugin file %s contains more than one line that "
                    "could be interpreted as a module name" % fn)
            module_name = line
        if module_name is None:
            raise PluginNotFound(
                "Plugin file %s does not contain a module name" % fn)
        return module_name
    finally:
        f.close()
