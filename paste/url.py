"""
This module implements a class for handling URLs.
"""
import urllib
import cgi

__all__ = ["URL", "Image"]

def html_quote(v):
    if v is None:
        return ''
    return cgi.escape(str(v), 1)

def url_quote(v):
    if v is None:
        return ''
    return urllib.quote(str(v))

url_unquote = urllib.unquote

def js_repr(v):
    if v is None:
        return 'null'
    elif v is False:
        return 'false'
    elif v is True:
        return 'true'
    elif isinstance(v, list):
        return '[%s]' % ', '.join(map(js_repr, v))
    elif isinstance(v, dict):
        return '{%s}' % ', '.join(
            ['%s: %s' % (js_repr(key), js_repr(value))
             for key, value in v])
    elif isinstance(v, str):
        return repr(v)
    elif isinstance(v, unicode):
        # @@: how do you do Unicode literals in Javascript?
        return repr(v.encode('UTF-8'))
    elif isinstance(v, (float, int)):
        return repr(v)
    elif isinstance(v, long):
        return repr(v).lstrip('L')
    elif hasattr(v, '__js_repr__'):
        return v.__js_repr__()
    else:
        raise ValueError(
            "I don't know how to turn %r into a Javascript representation"
            % v)

class URLResource(object):

    """
    This is an abstract superclass for different kinds of URLs
    """

    default_params = {}

    def __init__(self, url, vars=None, attrs=None,
                 params=None):
        self.url = url or '/'
        self.vars = vars or []
        self.attrs = attrs or {}
        self.params = self.default_params.copy()
        self.original_params = params or {}
        if params:
            self.params.update(params)

    def __call__(self, *args, **kw):
        res = self._add_positional(args)
        res = res._add_vars(kw)
        return res

    def __getitem__(self, item):
        if '=' in item:
            name, value = item.split('=', 1)
            return self._add_vars({url_unquote(name): url_unquote(value)})
        return self._add_positional((item,))

    def attr(self, **kw):
        for key in kw.keys():
            if key.endswith('_'):
                kw[key[:-1]] = kw[key]
                del kw[key]
        new_attrs = self.attrs.copy()
        new_attrs.update(kw)
        return self.__class__(self.url, vars=self.vars,
                              attrs=new_attrs,
                              params=self.original_params)

    def param(self, **kw):
        new_params = self.original_params.copy()
        new_params.update(kw)
        return self.__class__(self.url, vars=self.vars,
                              attrs=self.attrs,
                              params=new_params)

    def var(self, **kw):
        for key in kw.keys():
            if key.endswith('_'):
                kw[key[:-1]] = kw[key]
                del kw[key]
        new_vars = self.vars + kw.items()
        return self.__class__(self.url, vars=new_vars,
                              attrs=self.attrs,
                              params=self.original_params)

    def addpath(self, *paths):
        u = self
        for path in paths:
            path = path.lstrip('/')
            new_url = u.url
            if not new_url.endswith('/'):
                new_url += '/'
            u = u.__class__(new_url+path, vars=u.vars,
                            attrs=u.attrs,
                            params=u.original_params)
        return u
            
    __div__ = addpath

    def become(self, OtherClass):
        return OtherClass(self.url, vars=self.vars,
                          attrs=self.attrs,
                          params=self.original_params)
    
    def href__get(self):
        s = self.url
        if self.vars:
            s += '?'
            s += '&'.join(['%s=%s' % (url_quote(n), url_quote(v))
                           for n, v in self.vars])
        return s

    href = property(href__get)

    def __repr__(self):
        base = '<%s %s' % (self.__class__.__name__,
                           self.href or "''")
        if self.attrs:
            base += ' attrs(%s)' % (
                ' '.join(['%s="%s"' % (html_quote(n), html_quote(v))
                          for n, v in self.attrs.items()]))
        if self.original_params:
            base += ' params(%s)' % (
                ', '.join(['%s=%r' % (n, v)
                           for n, v in self.attrs.items()]))
        return base + '>'
    
    def html__get(self):
        if not self.params.get('tag'):
            raise ValueError(
                "You cannot get the HTML of %r until you set the "
                "'tag' param'" % self)
        content = self._get_content()
        tag = '<%s' % self.params.get('tag')
        attrs = ' '.join([
            '%s="%s"' % (html_quote(n), html_quote(v))
            for n, v in self._html_attrs()])
        if attrs:
            tag += ' ' + attrs
        tag += self._html_extra()
        if content is None:
            return tag + ' />'
        else:
            return '%s>%s</%s>' % (tag, content, self.params.get('tag'))

    html = property(html__get)

    def _html_attrs(self):
        return self.attrs.items()

    def _html_extra(self):
        return ''

    def _get_content(self):
        """
        Return the content for a tag (for self.html); return None
        for an empty tag (like ``<img />``)
        """
        raise NotImplementedError
    
    def _add_vars(self, vars):
        raise NotImplementedError

    def _add_positional(self, args):
        raise NotImplementedError

class URL(URLResource):

    r"""
    >>> u = URL('http://localhost')
    >>> u
    <URL http://localhost>
    >>> u = u['view']
    >>> str(u)
    'http://localhost/view'
    >>> u['//foo'].param(content='view').html
    '<a href="http://localhost/view/foo">view</a>'
    >>> u.param(confirm='Really?', content='goto').html
    '<a href="http://localhost/view" onclick="return confirm(\'Really?\')">goto</a>'
    >>> u(title='See "it"', content='goto').html
    '<a href="http://localhost/view?title=See%20%22it%22">goto</a>'
    >>> u('another', var='fuggetaboutit', content='goto').html
    '<a href="http://localhost/view/another?var=fuggetaboutit">goto</a>'
    >>> u.attr(content='goto').html
    Traceback (most recent call last):
        ....
    ValueError: You must give a content param to <URL http://localhost/view attrs(content="goto")> generate anchor tags
    >>> str(u['foo=bar%20stuff'])
    'http://localhost/view?foo=bar%20stuff'
    """

    default_params = {'tag': 'a'}

    def __str__(self):
        return self.href

    def _get_content(self):
        if not self.params.get('content'):
            raise ValueError(
                "You must give a content param to %r generate anchor tags"
                % self)
        return self.params['content']

    def _add_vars(self, vars):
        url = self
        if 'confirm' in vars:
            url = url.param(confirm=vars.pop('confirm'))
        if 'content' in vars:
            url = url.param(content=vars.pop('content'))
        return url.var(**vars)

    def _add_positional(self, args):
        return self.addpath(*args)

    def _html_attrs(self):
        attrs = self.attrs.items()
        attrs.insert(0, ('href', self.href))
        if self.params.get('confirm'):
            attrs.append(('onclick', 'return confirm(%s)'
                          % js_repr(self.params['confirm'])))
        return attrs

    def onclick_goto__get(self):
        return 'location.href=%s; return false' % js_repr(self.href)

    onclick_goto = property(onclick_goto__get)

    def button__get(self):
        return self.become(Button)

    button = property(button__get)
            
class Image(URLResource):

    r"""
    >>> i = Image('/images')
    >>> i = i / '/foo.png'
    >>> i.html
    '<img src="/images/foo.png" />'
    >>> str(i['alt=foo'])
    '<img src="/images/foo.png" alt="foo" />'
    >>> i.href
    '/images/foo.png'
    """
    
    default_params = {'tag': 'img'}

    def __str__(self):
        return self.html

    def _get_content(self):
        return None

    def _add_vars(self, vars):
        return self.attr(**vars)

    def _add_positional(self, args):
        return self.addpath(*args)

    def _html_attrs(self):
        attrs = self.attrs.items()
        attrs.insert(0, ('src', self.href))
        return attrs

class Button(URLResource):

    r"""
    >>> u = URL('/')
    >>> u = u / 'delete'
    >>> b = u.button['confirm=Sure?'](id=5, content='del')
    >>> str(b)
    '<button onclick="if (confirm(\'Sure?\')) {location.href=\'/delete?id=5\'}; return false">del</button>'
    """

    default_params = {'tag': 'button'}

    def __str__(self):
        return self.html

    def _get_content(self):
        if self.params.get('content'):
            return self.params['content']
        if self.attrs.get('value'):
            return self.attrs['content']
        # @@: Error?
        return None

    def _add_vars(self, vars):
        button = self
        if 'confirm' in vars:
            button = button.param(confirm=vars.pop('confirm'))
        if 'content' in vars:
            button = button.param(content=vars.pop('content'))
        return button.var(**vars)

    def _add_positional(self, args):
        return self.addpath(*args)

    def _html_attrs(self):
        attrs = self.attrs.items()
        onclick = 'location.href=%s' % js_repr(self.href)
        if self.params.get('confirm'):
            onclick = 'if (confirm(%s)) {%s}' % (
                js_repr(self.params['confirm']), onclick)
        onclick += '; return false'
        attrs.insert(0, ('onclick', onclick))
        return attrs
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()
    
