"""
timeinterval

Convert interval strings (in the form of 1w2d, etc) to
seconds, and back again.  Is not exactly about months or
years (leap years in particular).

Accepts (y)ear, (b)month, (w)eek, (d)ay, (h)our, (m)inute, (s)econd.

Exports only time_encode and time_decode functions.  
"""

import re

second = 1
minute = second*60
hour = minute*60
day = hour*24
week = day*7
month = day*30
year = day*365
time_values = {
    'y': year,
    'b': month,
    'w': week,
    'd': day,
    'h': hour,
    'm': minute,
    's': second,
    }
time_ordered = time_values.items()
time_ordered.sort(lambda a, b: -cmp(a[1], b[1]))
    
def time_encode(seconds):
    """Encodes a number of seconds (representing a time interval)
    into a form like 1h2d3s."""
    s = ''
    for char, amount in time_ordered:
        if seconds >= amount:
            i, seconds = divmod(seconds, amount)
            s += '%i%s' % (i, char)
    return s

time_re = re.compile(r'[0-9]+[a-zA-Z]')
def time_decode(s):
    """Decodes a number in the format 1h4d3m (1 hour, 3 days, 3 minutes)
    into a number of seconds"""
    time = 0
    for match in all_matches(s, time_re):
        char = match.group(0)[-1].lower()
        if not time_values.has_key(char):
            # @@: should signal error
            continue
        time += int(match.group(0)[:-1]) * time_values[char]
    return time

def all_matches(source, regex):
    """
    Return a list of matches for regex in source
    """
    pos = 0
    end = len(source)
    rv = []
    match = regex.search(source, pos)
    while match:
        rv.append(match)
        match = regex.search(source, match.end() )
    return rv

__all__ = ['time_encode', 'time_decode']
