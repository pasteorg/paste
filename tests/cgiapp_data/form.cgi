#!/usr/bin/env python

print('Content-type: text/plain')
print('')

import sys
from os.path import dirname

base_dir = dirname(dirname(dirname(__file__)))
sys.path.insert(0, base_dir)

from paste.util.field_storage import FieldStorage

class FormFieldStorage(FieldStorage):

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
        error = None

        for candidate in self._key_candidates(key):
            if isinstance(candidate, bytes):
                # ouch
                candidate = repr(candidate)
            try:
                return super().__getitem__(candidate)
            except KeyError as e:
                if error is None:
                    error = e

        # fall through, re-raise the first KeyError
        raise error

    def __contains__(self, key):
        for candidate in self._key_candidates(key):
            if super().__contains__(candidate):
                return True
        return False


form = FieldStorage()

print('Filename:', form['up'].filename)
print('Name:', form['name'].value)
print('Content:', form['up'].file.read())
