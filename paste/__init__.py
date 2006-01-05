try:
    import pkg_resources
    pkg_resources.declare_namespace('paste')
except ImportError:
    # don't prevent use of paste if pkg_resources isn't installed
    pass
