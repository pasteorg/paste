# If true, then the svn revision won't be used to calculate the
# revision (set to True for real releases)
RELEASE = False

__version__ = "0.4"

from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
print 'PATH:', sys.path
import paste
print 'Paste PATH:', paste.__file__
from paste.util import finddata

setup(name="Paste",
      version=__version__,
      description="Tools for using a Web Server Gateway Interface stack",
      long_description="""\
These provide several pieces of "middleware" (or filters) that can be nested to build web applications.  Each
piece of middleware uses the WSGI (`PEP 333`_) interface, and should
be compatible with other middleware based on those interfaces.

.. _PEP 333: http://www.python.org/peps/pep-0333.html

Includes these features...

Testing
-------

* A fixture for testing WSGI applications conveniently and in-process,
  in ``paste.fixture``

* A fixture for testing command-line applications, also in
  ``paste.fixture``

* Check components for WSGI-compliance in ``paste.lint``

Dispatching
-----------

* Chain and cascade WSGI applications (returning the first non-error
  response) in ``paste.cascade``

* Dispatch to several WSGI applications based on URL prefixes, in
  ``paste.urlmap``

* Allow applications to make subrequests and forward requests
  internally, in ``paste.recursive``

Web Application
---------------

* Run CGI programs as WSGI applications in ``paste.cgiapp`` (and
  Python-sepcific CGI programs with ``paste.pycgiwrapper``)

* Traverse files and load WSGI applications from ``.py`` files (or
  static files), in ``paste.urlparser``

* Serve static directories of files, also in ``paste.urlparser``

Tools
-----

* Catch HTTP-related exceptions (e.g., ``HTTPNotFound``) and turn them
  into proper responses in ``paste.httpexceptions``

* Check for signed cookies for authentication, setting ``REMOTE_USER``
  in ``paste.login``

* Create sessions in ``paste.session`` and ``paste.flup_session``

* Gzip responses in ``paste.gzip``

* A wide variety of routines for manipulating WSGI requests and
  producing responses, in ``paste.wsgilib``

Debugging Filters
-----------------

* Catch (optionally email) errors with extended tracebacks (using
  Zope/ZPT conventions) in ``paste.exceptions``

* Catch errors presenting a `cgitb
  <http://python.org/doc/current/lib/module-cgitb.html>`_-based
  output, in ``paste.cgitb_catcher``.

* Profile each request and append profiling information to the HTML,
  in ``paste.profilemiddleware``

* Capture ``print`` output and present it in the browser for
  debugging, in ``paste.printdebug``

* Validate all HTML output from applications using the `WDG Validator
  <http://www.htmlhelp.com/tools/validator/>`_, appending any errors
  or warnings to the page, in ``paste.wdg_validator``

Other Tools
-----------

* A file monitor to allow restarting the server when files have been
  updated (for automatic restarting when editing code) in
  ``paste.reloader``

* A class for generating and traversing URLs, and creating associated
  HTML code, in ``paste.url``
""",
      classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='web application server wsgi',
      author="Ian Bicking",
      author_email="ianb@colorstudy.com",
      url="http://pythonpaste.org",
      license="MIT",
      packages=find_packages(exclude=['ez_setup', 'examples', 'packages']),
      package_data=finddata.find_package_data(),
      namespace_packages=['paste'],
      zip_safe=False,
      extras_require={
        'subprocess': [],
        'hotshot': [],
        'Flup': ['flup'],
        'Paste': [],
        },
      entry_points="""
      [paste.app_factory]
      cgi = paste.cgiapp:CGIApplication [subprocess]
      pycgi = paste.pycgiwrapper:CGIWrapper
      static = paste.urlparser:make_static

      [paste.composit_factory]
      urlmap = paste.urlmap:urlmap_factory
      cascade = paste.cascade:make_cascade

      [paste.filter_app_factory]
      error_catcher = paste.exceptions.errormiddleware:ErrorMiddleware
      cgitb = paste.cgitb_catcher:CgitbMiddleware
      flup_session = paste.flup_session:SessionMiddleware [Flup]
      gzip = paste.gzipper:middleware
      httpexceptions = paste.httpexceptions:middleware
      lint = paste.lint:middleware
      login = paste.login:middleware
      printdebug = paste.printdebug:PrintDebugMiddleware 
      profile = paste.profilemiddleware:ProfileMiddleware [hotshot]
      recursive = paste.recursive:RecursiveMiddleware
      # This isn't good enough to deserve the name egg:Paste#session:
      paste_session = paste.session:SessionMiddleware
      wdg_validate = paste.wdg_validate:WDGValidateMiddleware [subprocess]
      evalerror = paste.evalexception:EvalException
      """,
      )
