class Continue:
    """
    This class is a singleton (never meant to be instantiated) that
    represents a kind of no-op return from a class.
    """
    def __init__(self):
        assert False, (
            "Continue cannot be instantiated (use the class object "
            "itself)")

def wrap_func(func):
    name = func.__name__
    def replacement_func(actor, *args, **kw):
        # @@: It's really more of an "inner_value" than "next_method"
        kw['next_method'] = func
        result = raise_event('start_%s' % name, actor, *args, **kw)
        del kw['next_method']
        if result is Continue:
            value = func(actor, *args, **kw)
        else:
            return result
        result = raise_event('end_%s' % name, actor, value, *args, **kw)
        if result is Continue:
            return value
        return result
    replacement_func.__name__ = name
    return replacement_func

def raise_event(name, actor, *args, **kw):
    for listener in actor.listeners:
        value = listener(name, actor, *args, **kw)
        if value is not Continue:
            return value
    return Continue
