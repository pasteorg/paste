# Deprecated 18 Dec 2005
"""
Deprecated -- see ``paste.debug.profile``
"""
import warnings
from paste.debug.profile import *

__deprecated__ = True

warnings.warn(
    "The paste.profilemiddleware module has been moved to "
    "paste.debug.profile",
    DeprecationWarning, 2)

