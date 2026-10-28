# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)

import warnings
warnings.warn("Paste is not being actively maintained. Choose other options.",
              DeprecationWarning)

try:
    import modulefinder
except ImportError:
    pass
else:
    for p in __path__:
        modulefinder.AddPackagePath(__name__, p)
