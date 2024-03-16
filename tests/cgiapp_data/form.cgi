#!/usr/bin/env python

import sys

# Quiet warnings in this CGI so that it does not upset tests.
if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

# TODO: cgi is deprecated and will go away in Python 3.13.
import cgi

print('Content-type: text/plain')
print('')

if sys.version_info.major >= 3:
    # Python 3: cgi.FieldStorage keeps some field names as unicode and some as
    # the repr() of byte strings, duh.

    class FieldStorage(cgi.FieldStorage):

        def _key_candidates(self, key):
            yield key

            try:
                # assume bytes, coerce to str
                try:
                    yield key.decode(self.encoding)
                except UnicodeDecodeError:
                    pass
            except AttributeError:
                # assume str, coerce to bytes
                try:
                    yield key.encode(self.encoding)
                except UnicodeEncodeError:
                    pass

        def __getitem__(self, key):

            superobj = super(FieldStorage, self)

            error = None

            for candidate in self._key_candidates(key):
                if isinstance(candidate, bytes):
                    # ouch
                    candidate = repr(candidate)
                try:
                    return superobj.__getitem__(candidate)
                except KeyError as e:
                    if error is None:
                        error = e

            # fall through, re-raise the first KeyError
            raise error

        def __contains__(self, key):
            superobj = super(FieldStorage, self)

            for candidate in self._key_candidates(key):
                if superobj.__contains__(candidate):
                    return True
            return False

else: # PY2

    FieldStorage = cgi.FieldStorage


form = FieldStorage()

print('Filename: %s' % form['up'].filename)
print('Name: %s' % form['name'].value)
print('Content: %s' % form['up'].file.read())
