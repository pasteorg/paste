import sys
import os

third_party = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    '3rd-party')

new_python_path = os.path.join(third_party, 'new_python')

def load_new_module(module_name, python_version):
    """
    Modules in the standard library that have been improved can be
    loaded with this command.  python_version is a sys.version_info
    tuple, and if you need a newer version then we'll look in
    ../3rd-party/new_python/python/module.py; otherwise it'll return
    the normal module.  E.g.:

        doctest = load_new_module('doctest', (2, 4))
    """
    if python_version > sys.version_info:
        if new_python_path not in sys.path:
            sys.path.append(new_python_path)
        try:
            exec "import python.%s as generic_module" % module_name
        except ImportError, e:
            raise ImportError(
                "Cannot load backported (from python version %s) "
                "stdlib module %s; expected to find it in %s"
                % ('.'.join(map(str, python_version)),
                   module_name,
                   os.path.join(new_python_path, 'python')))
    else:
        exec "import %s as generic_module" % module_name
    return generic_module

def add_package(package_name):
    """
    If package_name has not been installed, we add the appropriate
    path from ../3rd-party/package_name-files

    *After* calling this function you can import the package on your
    own, either from the package the user installed, or from the
    package we distribute.
    """
    try:
        exec "import %s" % package_name
    except ImportError:
        path = os.path.join(third_party, '%s-files' % package_name)
        if os.path.exists(path):
            sys.path.append(path)
        else:
            raise ImportError(
                "Cannot load the package %s; expected to find it in "
                "%s.  Have you run build-pkg.py?"
                % (package_name, path))
