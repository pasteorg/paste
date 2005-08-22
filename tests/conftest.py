import sys
import os
import pkg_resources

pkg_resources.require('PasteDeploy')

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
