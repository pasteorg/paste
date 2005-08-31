# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

"""
Finds all modules in a packages, loads them, and returns them.
"""

import os
import re
from paste.util.import_string import import_module

module_name = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$')

def find_modules(package):
    pkg_name = package.__name__
    modules = []
    base = os.path.abspath(package.__file__)
    if os.path.basename(os.path.splitext(base)[0]) == '__init__':
        base = os.path.dirname(base)
    if os.path.isdir(base):
        for module_fn in os.listdir(base):
            base, ext = os.path.splitext(module_fn)
            full = os.path.join(base, module_fn)
            if not module_name.search(base):
                continue
            if (os.path.isdir(full)
                and os.path.exists(os.path.join(full, '__ini__.py'))):
                modules.extend(import_module(pkg_name + '.' + base))
            elif ext == '.py':
                modules.append(import_module(pkg_name + '.' + base))
    else:
        modules.append(package)
    return modules
