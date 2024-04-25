"""
Package for miscellaneous routines that do not depend on other parts
of Paste
"""


class NoDefault:
    """Sentinel for parameters without default value."""

    def __repr__(self):
        return '<NoDefault>'


NO_DEFAULT = NoDefault()
