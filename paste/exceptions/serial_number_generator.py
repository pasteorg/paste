"""
Creates a human-readable identifier, using numbers and digits,
avoiding ambiguous numbers and letters.  hash_identifier can be used
to create compact representations that are unique for a certain string
(or concatenation of strings)
"""

import md5

good_characters = "23456789abcdefghjkmnpqrtuvwxyz"

base = len(good_characters)

def make_identifier(number):
    """
    Encodes a number as an identifier.
    """
    if not isinstance(number, (int, long)):
        raise ValueError(
            "You can only make identifiers out of integers (not %r)"
            % number)
    if number < 0:
        raise ValueError(
            "You cannot make identifiers out of negative numbers: %r"
            % number)
    result = []
    while number:
        next = number % base
        result.append(good_characters[next])
        # Note, this depends on integer rounding of results:
        number = number / base
    return ''.join(result)

def hash_identifier(s, length, pad=True, hasher=md5, prefix='',
                    group=None, upper=False):
    """
    Hashes the string (with the given hashing module), then turns that
    hash into an identifier of the given length (using modulo to
    reduce the length of the identifier).  If ``pad`` is False, then
    the minimum-length identifier will be used; otherwise the
    identifier will be padded with 0's as necessary.

    ``prefix`` will be added last, and does not count towards the
    target length.  ``group`` will group the characters with ``-`` in
    the given lengths, and also does not count towards the target
    length.  E.g., ``group=4`` will cause a identifier like
    ``a5f3-hgk3-asdf``.  Grouping occurs before the prefix.
    """
    if length > 26 and hasher is md5:
        raise ValueError, (
            "md5 cannot create hashes longer than 26 characters in "
            "length (you gave %s)" % length)
    if isinstance(s, unicode):
        s = s.encode('utf-8')
    h = hasher.new(str(s))
    bin_hash = h.digest()
    modulo = base ** length
    number = 0
    for c in list(bin_hash):
        number = (number * 256 + ord(c)) % modulo
    ident = make_identifier(number)
    if pad:
        ident = good_characters[0]*(length-len(ident)) + ident
    if group:
        parts = []
        while ident:
            parts.insert(0, ident[-group:])
            ident = ident[:-group]
        ident = '-'.join(parts)
    if upper:
        ident = ident.upper()
    return prefix + ident

# doctest tests:
__test__ = {
    'make_identifier': """
    >>> make_identifier(0)
    ''
    >>> make_identifier(1000)
    '922'
    >>> make_identifier(-100)
    Traceback (most recent call last):
        ...
    ValueError: You cannot make identifiers out of negative numbers: -100
    >>> make_identifier('test')
    Traceback (most recent call last):
        ...
    ValueError: You can only make identifiers out of integers (not 'test')
    >>> make_identifier(1000000000000)
    '5bqderb62'
    """,
    'hash_identifier': """
    >>> hash_identifier(0, 5)
    'fg35w'
    >>> hash_identifier(0, 10)
    'fg35w4t7yv'
    >>> hash_identifier('this is a test of a long string', 5)
    'qpvbe'
    >>> hash_identifier(0, 26)
    'fg35w4t7yvwr8rxpr3g06xj7cf'
    >>> hash_identifier(0, 30)
    Traceback (most recent call last):
        ...
    ValueError: md5 cannot create hashes longer than 26 characters in length (you gave 30)
    >>> hash_identifier(0, 10, group=4)
    'fg-35w4-t7yv'
    >>> hash_identifier(0, 10, group=4, upper=True, prefix='M-')
    'M-FG-35W4-T7YV'
    """}

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    
