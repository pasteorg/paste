"""
A mostly dummy class to simulate the Webware Application object.
"""

from wkcommon import NoDefault

class Application(object):

    def __init__(self, transaction):
        self._transaction = transaction

    def forward(self, trans, url, context=None):
        assert context is None, "Contexts are not supported"
        trans.forward(url)

    def setting(self, setting, default=NoDefault):
        assert default is not NoDefault, "No settings are defined"
        return default
