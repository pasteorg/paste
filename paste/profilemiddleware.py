# Deprecated 18 Dec 2005
import warnings
from paste.debug.profile import *

warnings.warn(
    "The paste.profilemiddleware module has been moved to "
    "paste.debug.profile",
    DeprecationWarning, 2)

