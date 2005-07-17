#!/usr/bin/env python
"""
This is a very basic script to generate a site from a set of ReST
documents.
"""

import sys
import os
import re
import shutil
import optparse
from Cheetah.Template import Template
from paste import pyconfig

__version__ = '0.1'

parser = optparse.OptionParser(
    version=__version__,
    usage="%prog [OPTIONS]")

parser.add_option(
    '-f', '--config-file',
    dest='config_file',
    metavar='FILENAME',
    default='doc.conf',
    help="The configuration file to load (default doc.conf)")

def main():
    options, args = parser.parse_args()
    assert not args, (
        "No arguments are allowed")
    conf = pyconfig.Config(with_default=True)
    conf.load_dict({'dirs': {},
                    'dest_base': os.getcwd()})
    conf.load(options.config_file)
    dirs = conf['dirs']
    base = conf['dest_base']
    for source, dest in dirs.items():
        dirs[source] = os.path.join(base, dest)
    gen_site(conf)
    
def gen_site(conf):
    template = make_template(conf)
    files = find_files(conf)
    for source, dest in files.items():
        if not source.endswith('.html'):
            shutil.copyfile(source, dest)
            continue
        f = RestFile(source)
        template.ns.clear()
        f.update_ns(template.ns)
        content = str(template)
        print 'Writing %s (%i bytes)' % (os.path.basename(source), len(content))
        dest_dir = os.path.dirname(dest)
        if not os.path.exists(dest_dir):
            print 'Creating %s' % dest_dir
            os.makedirs(dest_dir)
        f = open(dest, 'w')
        f.write(content)
        f.close()

def find_files(conf):
    files = {}
    for source, dest in conf['dirs'].items():
        find_files_dir(source, dest, conf, files)
    return files

def find_files_dir(source, dest, conf, files):
    for name in os.listdir(source):
        source_fn = os.path.join(source, name)
        if os.path.isdir(source_fn):
            continue
        files[source_fn] = os.path.join(os.path.join(dest, name))

def make_template(conf):
    template_fn = os.path.join(os.getcwd(), conf['template'])
    ns = {}
    template = Template(
        file=template_fn, searchList=[ns])
    template.ns = ns
    return template
    
class RestFile(object):

    def __init__(self, fn):
        self.filename = fn
        f = open(fn)
        self.html = f.read()
        f.close()
        self.read_properties()
        self.read_content()

    def update_ns(self, ns):
        ns['file'] = self
        ns['content'] = self.content
        ns.update(self.properties)

    _title_re = re.compile(r'<title>(.*?)</title>')
    def read_properties(self):
        props = self.properties = {}
        m = self._title_re.search(self.html)
        if m:
            props['title'] = m.group(1)
        else:
            print 'No title in %s' % self.filename
            props['title'] = ''

    _start_re = re.compile(r'<div class=".*?" id="contents">')
    _end_re = re.compile(r'</div>[ \n]*</div>[ \n]*</body>')
    _bad_res = [
        (re.compile(r'<link rel="stylesheet".*?>'), ''),
        (re.compile(r'<h1 class="title">.*?</h1>'), ''),
        (re.compile(r'(<p class=".*?"><a name="contents">.*?</p>)[ \n]*'
                    r'(<ul class="simple">)'),
         '<div><ul class="simple contents">\n'
         '<li class="header">Contents</li>\n'),
        (re.compile(r'(<th class="docinfo-name">Date:</th>[ \n]*)'
                    r'(<td>).*?\((.*?)\)'),
         r'\1\2\3'),
    ]
    
    def read_content(self):
        c = self.html
        m = self._start_re.search(c)
        if m:
            c = c[m.end():]
        else:
            print 'Bad beginning in %s' % self.filename
        m = self._end_re.search(c)
        if m:
            c = c[:m.start()]
        else:
            print 'Bad ending in %s' % self.filename
        for regex, sub in self._bad_res:
            c = regex.sub(sub, c)
        self.content = c

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.filename)

if __name__ == '__main__':
    main()
    
