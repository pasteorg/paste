# (c) 2005 Ben Bangert
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""
OpenID Authentication (Consumer)

OpenID is a distributed authentication system for single sign-on originally
developed at/for LiveJournal.com.

    http://openid.net/
    
URL. You can have multiple identities in the same way you can have multiple
URLs. All OpenID does is provide a way to prove that you own a URL (identity). 
And it does this without passing around your password, your email address, or 
anything you don't want it to. There's no profile exchange component at all: 
your profiile is your identity URL, but recipients of your identity can then 
learn more about you from any public, semantically interesting documents 
linked thereunder (FOAF, RSS, Atom, vCARD, etc.).

``Note``: paste.auth.openid requires installation of the Python-OpenID
libraries::

    http://www.openidenabled.com/
"""

import cgi
import urlparse

def quoteattr(s):
    qs = cgi.escape(s, 1)
    return '"%s"' % (qs,)

# You may need to manually add the openid package into your
# python path if you don't have it installed with your system python.
# If so, uncomment the line below, and change the path where you have
# Python-OpenID.
# sys.path.append('/path/to/openid/')

from openid.store import filestore
from openid.consumer import consumer
from openid.oidutil import appendArgs

def AuthOpenIDHandler(application, data_store_path, login_url='/'):
    """
    This middleware implements OpenID Consumer behavior to authenticate a
    URL against an OpenID Server.
    """
    def auth_application(environ, start_response):
        store = filestore.FileOpenIDStore(data_store_path)
        oidconsumer = consumer.OpenIDConsumer(store)
        
        return application(environ, start_response)
    return auth_application

middleware = AuthOpenIDHandler
