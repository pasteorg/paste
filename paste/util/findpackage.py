import sys
import os

def find_package(dir):
    """
    Given a directory, finds the equivalent package name.  If it
    is directly in sys.path, returns ''.
    """
    orig_dir = dir
    path = sys.path
    packages = []
    last_dir = None
    while 1:
        if dir in path:
            return '.'.join(packages)
        packages.insert(0, os.path.basename(dir))
        dir = os.path.dirname(dir)
        if last_dir == dir:
            raise ValueError(
                "%s is not under any path found in sys.path" % orig_dir)
        last_dir = dir
    
