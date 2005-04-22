"""
WebUtils.Funcs provides some basic functions that are useful in HTML and web development.

You can safely import * from WebUtils.Funcs if you like.


TO DO

* Document the 'codes' arg of htmlEncode/Decode.

"""

import string


htmlCodes = [
	['&', '&amp;'],
	['<', '&lt;'],
	['>', '&gt;'],
	['"', '&quot;'],
#	['\n', '<br>']
]

htmlCodesReversed = htmlCodes[:]
htmlCodesReversed.reverse()


def htmlEncode(s, codes=htmlCodes):
	""" Returns the HTML encoded version of the given string. This is useful to display a plain ASCII text string on a web page."""
	for code in codes:
		s = string.replace(s, code[0], code[1])
	return s

def htmlDecode(s, codes=htmlCodesReversed):
	""" Returns the ASCII decoded version of the given HTML string. This does NOT remove normal HTML tags like <p>. It is the inverse of htmlEncode(). """
	for code in codes:
		s = string.replace(s, code[1], code[0])
	return s



_urlEncode = {}
for i in range(256):
	_urlEncode[chr(i)] = '%%%02x' % i
for c in string.letters + string.digits + '_,.-/':
	_urlEncode[c] = c
_urlEncode[' '] = '+'

def urlEncode(s):
	""" Returns the encoded version of the given string, safe for using as a URL. """
	return string.join(map(lambda c: _urlEncode[c], list(s)), '')

def urlDecode(s):
	""" Returns the decoded version of the given string. Note that invalid URLs will throw exceptons. For example, a URL whose % coding is incorrect. """
	mychr = chr
	atoi = string.atoi
	parts = string.split(string.replace(s, '+', ' '), '%')
	for i in range(1, len(parts)):
		part = parts[i]
		parts[i] = mychr(atoi(part[:2], 16)) + part[2:]
	return string.join(parts, '')


def htmlForDict(dict, addSpace=None, filterValueCallBack=None, maxValueLength=None):
	""" Returns an HTML string with a <table> where each row is a key-value pair. """
	keys = dict.keys()
	keys.sort()
	# A really great (er, bad) example of hardcoding.  :-)
	html = ['<table width=100% border=0 cellpadding=2 cellspacing=2>']
	for key in keys:
		value = dict[key]
		if addSpace!=None  and  addSpace.has_key(key):
			target = addSpace[key]
			value = string.join(string.split(value, target), '%s '%target)
		if filterValueCallBack:
			value = filterValueCallBack(value, key, dict)
		value = str(value)
		if maxValueLength and len(value) > maxValueLength:
			value = value[:maxValueLength] + '...'
		html.append('<tr bgcolor=#F0F0F0> <td> %s </td> <td> %s &nbsp;</td> </tr>\n' % (htmlEncode(str(key)), htmlEncode(value)))
	html.append('</table>')
	return string.join(html, '')


def requestURI(dict):
	""" Returns the request URI for a given CGI-style dictionary. Uses REQUEST_URI if available, otherwise constructs and returns it from SCRIPT_NAME, PATH_INFO and QUERY_STRING. """
	uri = dict.get('REQUEST_URI', None)
	if uri==None:
		uri = dict.get('SCRIPT_NAME', '') + dict.get('PATH_INFO', '')
		query = dict.get('QUERY_STRING', '')
		if query!='':
			uri = uri + '?' + query
	return uri

def normURL(path):
        """Normalizes a URL path, like os.path.normpath, but acts on
        a URL independant of operating system environmant.
        """
        if not path:
                return
        
        initialslash = path[0] == '/'
        lastslash = path[-1] == '/'
        comps = string.split(path, '/')
        
        newcomps = []
        for comp in comps:
                if comp in ('','.'):
                        continue
                if comp != '..':
                        newcomps.append(comp)
                elif newcomps:
                        newcomps.pop()
        path = string.join(newcomps, '/')
        if path and lastslash:
                path = path + '/'
        if initialslash:
                path = '/' + path
        return path

### Deprecated

HTMLCodes = htmlCodes
HTMLCodesReversed = htmlCodesReversed

def HTMLEncode(s):
	print 'DEPRECATED: WebUtils.Funcs.HTMLEncode() on 02/24/01 in ver 0.3. Use htmlEncode() instead.'
	return htmlEncode(s)

def HTMLDecode(s):
	print 'DEPRECATED: WebUtils.Funcs.HTMLDecode() on 02/24/01 in ver 0.3. Use htmlDecode() instead.'
	return htmlDecode(s)

def URLEncode(s):
	print 'DEPRECATED: WebUtils.Funcs.URLEncode() on 02/24/01 in ver 0.3. Use urlEncode() instead.'
	return urlEncode(s)

def URLDecode(s):
	print 'DEPRECATED: WebUtils.Funcs.URLDecode() on 02/24/01 in ver 0.3. Use urlDecode() instead.'
	return urlDecode(s)

def HTMLForDictionary(dict, addSpace=None):
	print 'DEPRECATED: WebUtils.Funcs.HTMLForDictionary() on 02/24/01 in ver 0.3. Use htmlForDict() instead.'
	return htmlForDict(dict, addSpace)

def RequestURI(dict):
	print 'DEPRECATED: WebUtils.Funcs.RequestURI() on 02/24/01 in ver 0.3. Use requestURI() instead.'
	return requestURI(dict)
