__all__ = ['looper']

class looper(object):
    """
    Use this like::

        for loop, item in looper(seq):
            if loop.first:...
    """

    def __init__(self, seq):
        self.seq = seq

    def __iter__(self):
        return looper_iter(self.seq)

    def __repr__(self):
        return '<%s for %r>' % (
            self.__class__.__name__, self.seq)

class looper_iter(object):

    def __init__(self, seq):
        self.seq = list(seq)
        self.pos = 0

    def __iter__(self):
        return self

    def next(self):
        if self.pos >= len(self.seq):
            raise StopIteration
        result = loop_pos(self.seq, self.pos), self.seq[self.pos]
        self.pos += 1
        return result

class loop_pos(object):

    def __init__(self, seq, pos):
        self.seq = seq
        self.pos = pos

    def __repr__(self):
        return '<loop pos=%r at %r>' % (
            self.seq[pos], pos)

    def index(self):
        return self.pos
    index = property(index)

    def count(self):
        return self.pos + 1
    count = property(count)

    def item(self):
        return self.seq[pos]
    item = property(item)

    def next(self):
        try:
            return self.seq[self.pos+1]
        except IndexError:
            return None
    next = property(next)

    def previous(self):
        if self.pos == 0:
            return None
        return self.seq[self.pos-1]
    previous = property(previous)

    def odd(self):
        return not self.pos % 2
    odd = property(odd)

    def even(self):
        return self.pos % 2
    even = property(even)

    def first(self):
        return self.pos == 0
    first = property(first)

    def last(self):
        return self.pos == len(self.seq)-1
    last = property(last)

    def new_group(self, getter=None):
        """
        Returns true if this item is the start of a new group,
        where groups mean that some attribute has changed.  The getter
        can be None (the item itself changes), an attribute name like
        ``'.attr'``, a function, or a dict key or list index.
        """
        if self.first:
            return True
        if getter is None:
            return self.item != self.previous
        elif (isinstance(getter, basestring)
              and getter.startswith('.')):
            getter = getter[1:]
            return getattr(self.item, getter) != getattr(self.previous, getter)
        elif callable(getter):
            return getter(self.item) != getter(self.previous)
        else:
            return self.item[getter] != self.previous[getter]
    
