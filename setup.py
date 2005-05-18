from distutils.core import setup
from distutils import sysconfig
import warnings
warnings.filterwarnings("ignore", "Unknown distribution option")

import sys
# patch distutils if it can't cope with the "classifiers" keyword
if sys.version < '2.2.3':
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None

import os

BASEDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'paste')
DATA_PREFIX = sysconfig.get_python_lib(prefix='')


def get_data_files(relpath, files=None):
    files = files or []
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
print package_data

setup(name="Paste",
      version="0.1",
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
                "paste.servers",
                "paste.servers.scgi_server",
                "paste.wareweb"],
      scripts=['scripts/paste-server', 'scripts/paste-setup'],
      download_url="",
      package_data={'paste': package_data},
      )

# Send announce to:
#   web-sig@python.org
#   python-announce@python.org
#   python-list@python.org
