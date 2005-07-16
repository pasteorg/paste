require('setuptools')

from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

setup(name="flup"
      version="0.0",
      description="Tools for WSGI servers and clients",
      long_description="""\
This Python package is a random collection of WSGI modules I've
written. fcgi and publisher have long existed since I became
interested in Python web programming a few years ago. They have been
recently cleaned up and retrofitted with WSGI. The other modules just
followed as I explored the possibilities of WSGI.
""",
      classifiers=["Development Status :: 3 - Alpha",
                   "Intended Audience :: Developers",
                   "Programming Language :: Python",
                   "Topic :: Internet :: WWW/HTTP",
                   "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   ],
      keywords='web wsgi scgi',
      author='Allan Saddi',
      author_email='allan@saddi.com',
      url='http://www.saddi.com/software/flup/',
      packages=find_packages(),
      zip_safe=True,
      )

