import cgi
from UserDict import UserDict

def parse_fields(environ):
    fs = cgi.FieldStorage(
        environ['wsgi.input'],
        environ=environ,
        keep_blank_values=True,
        strict_parsing=False)
    try:
        keys = fs.keys()
    except TypeError:
        # Maybe an XML-RPC request
        keys = []
    d = {}
    for key in keys:
        value = fs[key]
        if not isinstance(value, list):
            if not value.filename:
                # Turn the MiniFieldStorage into a string:
                value = value.value
        else:
            value = [v.value for v in value]
        d[key] = value
    if environ['REQUEST_METHOD'].upper() == 'POST':
        # Then we must also parse GET variables
        getfields = cgi.parse_qs(
            environ.get('QUERY_STRING', ''),
            keep_blank_values=True,
            strict_parsing=False)
        for name, value in getfields.items():
            if not d.has_key(name):
                if isinstance(value, list) and len(value) == 1:
                    # parse_qs always returns a list of lists,
                    # while FieldStorage only uses lists for
                    # keys that actually repeat; this fixes that.
                    value = value[0]
                d[name] = value
    return d

class Fields(UserDict):

    def __init__(self, field_dict):
        self.data = field_dict

    def __getattr__(self, attr):
        # @@: I don't like this.  Should it give a KeyError?
        # should it exist at all?
        return self.data.get(attr)

    def getlist(self, name):
        """
        Return the named item as a list ([] if name not found,
        [self[name]] if only one field passed in).
        """
        v = self.data.get(name, [])
        if isinstance(v, list):
            return v
        return [v]

    def itemlist(self):
        """
        Return a list of (name, [values...]).  Like .items(),
        except all values becomes a list (like .getlist()).
        """
        items = []
        for name, value in self.iteritems():
            if isinstance(value, list):
                items.append((name, value))
            else:
                items.append((name, [value]))
        return items
    
