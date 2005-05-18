from paste import wsgilib
from optparse import Option

def serve(conf, app):
    url = conf.get('url', '/')
    query_string = ''
    if '?' in url:
        url, query_string = url.split('?', 1)
    quiet = conf.get('quiet', False)
    status, headers, content, errors = wsgilib.raw_interactive(
        app, url, QUERY_STRING=query_string)
    any_header = False
    if not quiet or int(status.split()[0]) != 200:
        print 'Status:', status
        any_header = True
    for header, value in headers:
        if quiet and (
            header.lower() in ('content-type', 'content-length')
            or (header.lower() == 'set-cookie'
                and value.startswith('_SID_'))):
            continue
        print '%s: %s' % (header, value)
        any_header = True
    if any_header:
        print
    if conf.get('compact', False):
        # Remove empty lines
        content = '\n'.join([l for l in content.splitlines()
                             if l.strip()])
    print content
    if errors:
        sys.stderr.write('-'*25 + ' Errors ' + '-'*25 + '\n')
        sys.stderr.write(errors + '\n')

description = """\
Displays a single request to stdout
"""

options = [
    Option('--url',
           metavar='URL',
           help="The URL (not including domain or port!) to GET"),
    ]
