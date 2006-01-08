# (c) 2005 Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# Some of this code was funded by: http://prometheusresearch.com
"""
Date, Time, and Timespan Parsing Utilities

This module contains parsing support to create "human friendly" datetime
parsing. Many date/time parsing approaches depend upon the user entering
dates/times in a strict format and raising an error if their input
deviates.  By contrast, this module does the best it can with the input
producing a value given any human input; its expected that the output of
this module will be presented to the user for "confirmation" if it
differs from what they typed.  In other words, rather than giving an
error, it corrects the value.

This module supports three functions:

  ``parse_date``

     This function takes values like '9 jan 2007' and returns an
     ISO 8601 formatted date such as '2007-01-09'.

  ``parse_time``

     This function takes a time of daay, like '9AM' and returns the
     value in 24-hour clock style: '09:00'.

  ``parse_timedelta``

     This function takes a time interval, like '1h 15min' and
     returns the corresponding ``datetime.timedelta`` object.

The result of these functions is a normalized string value that has
predictable format (ie, can be easily parsed).
"""
import datetime
import string
import time, sys

__all__ = ['parse_timedelta', 'normalize_timedelta',
           'parse_time', 'normalize_time',
           'parse_date', 'normalize_date']

def _number(val):
    try:
        return string.atoi(val)
    except:
        return None

#
# timedelta
#
def _timedelta(val):
    val = string.lower(val)
    if "." in val:
        val = float(val)
        val = "%s:%s" % ( int(val) , 60 * ( val % 1.0))
    fHour = ("h" in val or ":" in val)
    fMin  = ("m" in val or ":" in val)
    fFraction = "." in val
    for noise in "minu:teshour().":
        val = string.replace(val,noise,' ')
    val = string.strip(val)
    val = string.split(val)
    hr = 0.0
    mi = 0
    val.reverse()
    if fHour: hr = float(val.pop())
    if fMin:  mi = int(val.pop())
    if len(val) > 0 and not hr:
        hr = float(val.pop())
    return (hr + mi / 60, mi % 60)

def parse_timedelta(val):
    """
    returns a ``datetime.timedelta`` object
    """
    if not val:
        return None
    (hr, mi) = _timedelta(val)
    return datetime.timedelta(hours=hr, minutes=mi)

def normalize_timedelta(val):
    """
    produces a normalized string value of the timedelta

    This module returns a normalized time span value consisting of
    the number of hours and minutes in clock form.  For example 1h
    and 15min is formatted as 01:15.
    """
    if not val:
        return ''
    return "%02d:%02d" % _timedelta(val)

#
# time
#
def _time(val):
    try:
        hr = None
        mi = None
        val = string.lower(val)
        amflag = (-1 != string.find(val,'a'))  # set if AM is found
        pmflag = (-1 != string.find(val,'p'))  # set if PM is found
        zzflag = (-1 != string.find(val,'00')) # if 'o hundred found
        for noise in (':','a','p','m','00',';','.'):
            val = string.replace(val,noise,' ')
        val = string.split(val)
        if len(val) > 1:
            hr = _number(val[0])
            mi = _number(val[1])
        else:
            val = val[0]
            if len(val) < 1:
                pass
            elif 'now' == val:
                tm = time.localtime()
                hr = tm[3]
                mi = tm[4]
            elif len(val) < 3:
                hr = _number(val)
                if     not amflag and not pmflag \
                   and not zzflag and hr < 7:
                         hr += 12
            elif len(val) < 5:
                hr = _number(val[:-2])
                mi = _number(val[-2:])
            else:
                hr = _number(val[:1])
    finally:
        pass
    if hr is None: hr = 12
    if mi is None: mi = 0
    if amflag  and hr >= 12: hr = hr - 12
    if pmflag  and hr < 12 : hr = hr + 12
    if hr >= 24 or hr < 0  : hr = 0
    if mi > 59  or mi < 0  : mi = 0
    return (hr, mi)

def parse_time(val):
    if not val:
        return None
    (hi,mi) = _time(val)
    return datetime.time(hr,mi)

def _format_time(value, ampm):
    (hr,mi) = value
    if not ampm:
        return "%02d:%02d" % (hr,mi)
    am = "AM"
    pos = "+"
    neg = "-"
    if hr < 1 or hr > 23:
        hr = 12
    elif hr >= 12:
        am = "PM"
        if hr > 12:
            hr = hr - 12
    return "%02d:%02d %s" % (hr,mi,am)

def normalize_time(val, ampm=False):
    return _format_time(_time(val),ampm)

#
# Date Processing
#

_one_day = datetime.timedelta(days=1)

_str2num = { 'jan':1, 'feb':2, 'mar':3, 'apr':4,  'may':5, 'jun':6,
            'jul':7, 'aug':8, 'sep':9, 'oct':10, 'nov':11, 'dec':12 }
def _month(val):
    for (key,mon) in _str2num.items():
        if key in val:
            return mon
    return None

_days_in_month = {1:31,2:28,3:31,4:30,5:31,6:30,
                 7:31,8:31,9:30,10:31,11:30,12:31 }
num2str = { 1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun',
            7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec' }
wkdy = ("mon","tue","wed","thu","fri","sat","sun" )

def _date(val):
    if not(val):
        return None
    dy = None
    yr = None
    mo = None
    # regular expressions would be good here...
    val = string.lower(val)
    chk = val[:3]
    now = None
    strict = val.split("-")
    if len(strict) == 3:
        (y,m,d) = strict
        if "+" in d:
            d = d.split("+")[0]
        if " " in d:
            d = d.split(" ")[0]
        now = datetime.date(int(y),int(m),int(d))
        val = "xxx" + val[10:]
    if not now and 'now' == chk:
        now = datetime.date.today()
    if not now and chk in wkdy:
        now = datetime.date.today()
        idx = list(wkdy).index(chk)
        while now.day_of_week != idx:
            now += _one_day
    if now:
        tail = val[3:].strip()
        tail = tail.replace("+"," +").replace("-"," -")
        for item in tail.split():
            try:
                days = int(item)
            except ValueError:
                pass
            else:
                now += datetime.timedelta(days=days)
        return (now.year,now.month,now.day,0, 0, 0, 0, 0, 0)
    #
    for noise in ('/','-',',','*'):
        val = string.replace(val,noise,' ')
    for noise in wkdy:
        val = string.replace(val,noise,' ')
    out = []
    last = False
    ldig = False
    for ch in val:
        if ch.isdigit():
            if last and not ldig:
               out.append(' ')
            last = ldig = True
        else:
            if ldig:
                out.append(' ')
                ldig = False
            last = True
        out.append(ch)
    val = string.split("".join(out))
    if 3 == len(val):
        a = _number(val[0])
        b = _number(val[1])
        c = _number(val[2])
        if len(val[0]) == 4:
            yr = a
            if b:  # 1999 6 23
                mo = b
                dy = c
            else:  # 1999 Jun 23
                mo = _month(val[1])
                dy = c
        elif a > 0:
            yr = c
            if len(val[2]) < 4:
                raise TypeError("four digit year required")
            if b: # 6 23 1999
                dy = b
                mo = a
            else: # 23 Jun 1999
                dy = a
                mo = _month(val[1])
        else: # Jun 23, 2000
            dy = b
            yr = c
            if len(val[2]) < 4:
                raise TypeError("four digit year required")
            mo = _month(val[0])
    elif 2 == len(val):
        a = _number(val[0])
        b = _number(val[1])
        if a > 999:
            yr = a
            dy = 1
            if b > 0: # 1999 6
                mo = b
            else: # 1999 Jun
                mo = _month(val[1])
        elif a > 0:
            if b > 999: # 6 1999
                mo = a
                yr = b
                dy = 1
            elif b > 0: # 6 23
                mo = a
                dy = b
            else: # 23 Jun
                dy = a
                mo = _month(val[1])
        else:
            if b > 999: # Jun 2001
                yr = b
                dy = 1
            else:  # Jun 23
                dy = b
            mo = _month(val[0])
    elif 1 == len(val):
        val = val[0]
        if not val.isdigit():
            mo = _month(val)
            if mo is not None:
                dy = 1
        else:
            v = _number(val)
            val = str(v)
            if 8 == len(val): # 20010623
                yr = _number(val[:4])
                mo = _number(val[4:6])
                dy = _number(val[6:])
            elif len(val) in (3,4):
                if v > 1300: # 2004
                    yr = v
                    mo = 1
                    dy = 1
                else:        # 1202
                    mo = _number(val[:-2])
                    dy = _number(val[-2:])
            elif v < 32:
                dy = v
            else:
                raise TypeError("four digit year required")
    tm = time.localtime()
    if mo is None: mo = tm[1]
    if dy is None: dy = tm[2]
    if yr is None: yr = tm[0]
    if mo > 12 or mo < 1: mo = 1
    if dy < 1: dy = 1
    max = _days_in_month[mo]
    if 2 == mo:
        if not(yr%400) or ( not(yr%4) and yr%100 ):
            max = 29
        else:
            max = 28
    if dy > max:
        raise TypeError("day too large for %s %s: '%s'" % \
               (num2str[mo], yr, dy))
    return (yr,mo,dy)

def _format_date(val, iso8601=True):
    if iso8601:
        return "%4d-%02d-%02d" % (val[0],val[1],val[2])
    return "%02d %s %4d" % (val[2],num2str[val[1]],val[0])

def parse_date(val, iso8601=True):
    if not val:
        return None
    (yr,mo,dy) = _date(val)
    return datetime.date(yr,mo,dy)

def normalize_date(val, iso8601=True):
    if not val:
        return ''
    return _format_date(_date(val),iso8601)


