# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# Deprecated 18 Dec 2005
"""
Deprecated -- see ``paste.debug.prints``
"""
import warnings
from paste.debug.prints import *

__deprecated__ = True

warnings.warn(
    "The paste.printdebug module has been moved to "
    "paste.debug.prints",
    DeprecationWarning, 2)

