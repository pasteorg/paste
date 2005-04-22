#!/usr/bin/env python

import cgiserver
import pycgiwrapper
cgiserver.run_with_cgi(
    pycgiwrapper.CGIWrapper('helloworld.cgi'))
