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

BASEDIR = os.path.split(os.path.abspath(__file__))[0]

def get_data_files(path, files = []):
    l = []
    for name in os.listdir(path):
        if name[0] == ".":
            continue
        relpath = os.path.join(path, name)
        f = os.path.join(BASEDIR, relpath)
        if os.path.isdir(f):
            get_data_files(relpath, files)
        elif os.path.isfile(f):
            l.append(f)
    pref = sysconfig.get_python_lib()[len(sysconfig.PREFIX) + 1:] 
    files.append((os.path.join(pref, path), l)) 
    return files

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
      data_files=get_data_files(os.path.join("paste","app_templates")) +
          [(os.path.join(sysconfig.get_python_lib()[len(sysconfig.PREFIX) + 1:], "paste"), [os.path.join("paste", "default_config.conf")])]
      )

# Send announce to:
#   web-sig@python.org
#   python-announce@python.org
#   python-list@python.org
