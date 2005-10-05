# Note: you may want to copy this into your setup.py file verbatim, as
# you can't import this from another package, when you don't know if
# that package is installed yet.

import os
from fnmatch import fnmatchcase
from distutils.util import convert_path

def find_package_data(where='.', package='', wildcards=(),
                      exclude_directories=('.*', 'CVS', '_darcs'),
                      only_in_packages=True):
    """
    Return a dictionary suitable for use in ``package_data``
    in a distutils ``setup.py`` file.

    The dictionary looks like::

        {'package': [wildcards]}

    Except for any directories under the package (that aren't
    themselves subpackages) it will expand the wildcards.  So if you
    have a package ``pygo`` and a subdirectory ``static`` (with no
    ``__init__.py`` file, hence not a subpackages) and
    ``wildcards=('*.css', '*.js')``, then you'll get::

        {'pygo': ['*.css', '*.js', 'static/*.css', 'static/*.js']}

    If ``only_in_packages`` is true, then top-level directories that
    are not packages won't be included (but directories under packages
    will).

    Directories matching any pattern in ``exclude_directories`` will
    be ignored; by default directories with leading ``.``, ``CVS``,
    and ``_darcs`` will be ignored.
    """
    out = {}
    stack = [(convert_path(where), '', package, only_in_packages)]
    while stack:
        where, prefix, package, only_in_packages = stack.pop(0)
        if package or not only_in_packages:
            out.setdefault(package, []).extend([
                prefix + wildcard
                for wildcard in wildcards])
        for name in os.listdir(where):
            fn = os.path.join(where, name)
            if not os.path.isdir(fn):
                continue
            bad_name = False
            for pattern in exclude_directories:
                if fnmatchcase(name, pattern):
                    bad_name = True
                    break
            if bad_name:
                continue
            if os.path.isfile(os.path.join(fn, '__init__.py')):
                if not package:
                    new_package = name
                else:
                    new_package = package + '.' + name
                stack.append((fn, '', new_package, False))
            else:
                stack.append((fn, prefix + name + '/', package, only_in_packages))
    return out

# Provided as an attribute, so you can append to these instead
# of replicating them:
standard_exclude = ('*.py', '*.pyc', '*~', '.*', '*.bak')

def enumerate_package_data(
    where='.', package='',
    exclude=standard_exclude,
    exclude_directories=('.*', 'CVS', '_darcs'),
    only_in_packages=True):
    """
    Return a dictionary suitable for use in ``package_data``
    in a distutils ``setup.py`` file.

    The dictionary looks like::

        {'package': [files]}

    Where ``files`` is a list of all the files in that package that
    don't match anything in ``exclude``.

    If ``only_in_packages`` is true, then top-level directories that
    are not packages won't be included (but directories under packages
    will).

    Directories matching any pattern in ``exclude_directories`` will
    be ignored; by default directories with leading ``.``, ``CVS``,
    and ``_darcs`` will be ignored.
    """
    out = {}
    stack = [(convert_path(where), '', package, only_in_packages)]
    while stack:
        where, prefix, package, only_in_packages = stack.pop(0)
        for name in os.listdir(where):
            fn = os.path.join(where, name)
            if os.path.isdir(fn):
                bad_name = False
                for pattern in exclude_directories:
                    if fnmatchcase(name, pattern):
                        bad_name = True
                        break
                if bad_name:
                    continue
                if os.path.isfile(os.path.join(fn, '__init__.py')):
                    if not package:
                        new_package = name
                    else:
                        new_package = package + '.' + name
                    stack.append((fn, '', new_package, False))
                else:
                    stack.append((fn, prefix + name + '/', package, only_in_packages))
            elif package or not only_in_packages:
                # is a file
                bad_name = False
                for pattern in exclude:
                    if fnmatchcase(name, pattern):
                        bad_name = True
                        break
                if bad_name:
                    continue
                out.setdefault(package, []).append(prefix+name)
    return out

if __name__ == '__main__':
    import sys, pprint
    if sys.argv[1] == 'enumerate':
        pprint.pprint(
            enumerate_package_data())
    else:
        pprint.pprint(
            find_package_data(wildcards=sys.argv[1:]))
