import warnings
# Deprecated Mar 3 2006 (remove quickly: April 2006)
warnings.warn(
    'paste.error_document has been moved to paste.errordocument'
    DeprecationWarning, 2)
from paste.errordocument import *
