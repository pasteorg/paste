"""
This module provides the basic metadata_real classes, but without any
functionality.  This way the import is fast and low-overhead.  But
when running docsupport.extract it will replace this module with the
real (more functional) thing.

Everything here is stubs.
"""

class DocItem(object):

    def __init__(self, *args, **kw):
        pass

WSGIKey = DocItem
Config = DocItem
Attribute = DocItem

    
