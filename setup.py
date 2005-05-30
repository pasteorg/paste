# If true, then the svn revision won't be used to calculate the
# revision (set to True for real releases)
RELEASE = False

__version__ = "0.0"

# Setup setuptools:
import sys
import os
base_paste_url = 'http://peak.telecommunity.com/dist/'
python_version = '%s.%s' % (sys.version_info[0], sys.version_info[1])
setuptools_version = '0.3a2'
support_dir = os.path.join(os.path.dirname(__file__), 'support')
setuptools_filename = 'setuptools-%s-py%s.egg' % (
    setuptools_version, python_version)
full_filename = os.path.join(support_dir, setuptools_filename)
if not os.path.exists(full_filename):
    if not os.path.exists(support_dir):
        os.mkdir(support_dir)
    print 'Downloading %s' % setuptools_filename
    setuptools_url = base_paste_url + setuptools_filename
    print 'Downloading from %s' % setuptools_url
    import urllib2
    import shutil
    f_in = urllib2.urlopen(setuptools_url)
    f_out = open(full_filename, 'wb')
    shutil.copyfileobj(f_in, f_out)
    f_in.close()
    f_out.close()
if full_filename not in sys.path:
    sys.path.append(full_filename)

from setuptools import setup

BASEDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'paste')

def get_data_files(relpath, files=None):
    if files is None:
        files = []
    for name in os.listdir(os.path.join(BASEDIR, relpath)):
        if name.startswith("."):
            continue
        fn = os.path.join(relpath, name)
        if os.path.isdir(os.path.join(BASEDIR, fn)):
            get_data_files(fn, files)
        elif os.path.isfile(os.path.join(BASEDIR, fn)):
            files.append(fn)
    return files

package_data = []
for subdir in [('app_templates',),
               ('frameworks',)]:
    package_data.extend(get_data_files(os.path.join(*subdir)))
for filename in [('default_config.conf',)]:
    package_data.append(os.path.join(*filename))

def get_svn_revision():
    """
    Returns the newest svn revision for all files in the this
    directory.
    """
    import commands
    status, output = commands.getstatusoutput(
        'svn ls -v %s' % os.path.dirname(__file__))
    if status:
        return 'unknown'
    max_revision = 0
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        revision = int(line.split()[0])
        max_revision = max(max_revision, revision)
    return max_revision

if not RELEASE:
    rev = get_svn_revision()
    __version__ += '-devel-r%s' % rev

setup(name="Paste",
      version=__version__,
      description="Tools for use with a Web Server Gateway Interface stack",
      long_description="""\
These provide several pieces of "middleware" that can be nested to build
web applications.  Each piece of middleware uses the WSGI (`PEP 333`_)
interface, and should be compatible with other middleware based on those
interfaces.

.. _PEP 333: http://www.python.org/peps/pep-0333.html

As an example (and a working implementation), a version Webware
(http://webwareforpython.org) is included, built from these tools with
wrappers to provide the Webware API on top of the middleware
functionality.
""",
      classifiers=["Development Status :: 3 - Alpha",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: Python Software Foundation License",
                   "Programming Language :: Python",
                   "Topic :: Internet :: WWW/HTTP",
                   "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   ],
      author="Ian Bicking",
      author_email="ianb@colorstudy.com",
      url="http://webwareforpython.org",
      license="PSF",
      packages=["paste", "paste.exceptions",
                "paste.util",
                "paste.webkit",
                "paste.webkit.FakeWebware",
                "paste.webkit.FakeWebware.WebKit",
                "paste.webkit.FakeWebware.WebUtils",
                "paste.webkit.FakeWebware.MiscUtils",
                "paste.webkit.FakeWebware.TaskKit",
                "paste.servers",
                "paste.servers.scgi_server",
                "paste.wareweb",
                "paste.docsupport",
                "paste.packaging",
                ],
      scripts=['scripts/paster'],
      download_url="",
      package_data={'paste': package_data},
      )

# Send announce to:
#   web-sig@python.org
#   python-announce@python.org
#   python-list@python.org
