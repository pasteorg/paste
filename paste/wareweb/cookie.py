from Cookie import SimpleCookie
import timeinterval

class Cookie(object):

    def __init__(self, name, value, path, expires=None, secure=False):
        self.name = name
        self.value = value
        self.path = path
        self.secure = secure
        if expires == 'ONCLOSE' or not expires:
            expires = None
        elif expires == 'NOW' or expires == 'NEVER':
            expires = time.gmtime(time.time())
            if expires == 'NEVER':
                expires = (expires[0] + 10,) + expires[1:]
            expires = time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", expires)
        else:
            if isinstance(expires, (str, unicode)) and expires.startswith('+'):
                interval = timeinterval.time_decode(expires[1:])
                expires = time.time() + interval
            if isinstance(expires, (int, long, float)):
                expires = time.gmtime(expires)
            if isinstance(expires, (tuple, time.struct_time)):
                expires = time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", expires)
        self.expires = expires

    def __repr__(self):
        return '<%s %s=%r>' % (
            self.__class__.__name__, self.name, self.value)

    def header(self):
        c = SimpleCookie()
        c[self.name] = value
        c[self.name]['path'] = self.path
        if self.expires is not None:
            c[self.name]['expires'] = expires
        if self.secure:
            c[self.name]['secure'] = True
        return str(c).split(':')[1].strip()
    
