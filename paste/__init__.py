# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
try:
    import pkg_resources
    pkg_resources.declare_namespace('paste')
except ImportError:
    # don't prevent use of paste if pkg_resources isn't installed
    pass
