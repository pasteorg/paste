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

