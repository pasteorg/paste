# Deprecated 18 Dec 2005
"""
Deprecated -- see ``paste.debug.wdg_validate``
"""
import warnings
from paste.debug.wdg_validate import *

__deprecated__ = True

warnings.warn(
    "The paste.wdg_validate module has been moved to "
    "paste.debug.wdg_validate",
    DeprecationWarning, 2)

