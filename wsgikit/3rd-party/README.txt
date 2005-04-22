This directory contains packages useful to Paste users, who may not
feel like installing those packages.  The module util.thirdparty has
functions for pulling these modules into the path, but also respecting
any packages the user installed on their own.

To use this, create a directory package_name-files, and then install
the package into that directory, probably like::

    cd PackageName
    python setup.py install \
      --install-lib=path/to/3rd-party/package_name-files

These files should *not* go into the repository!  But they should go
into the installation package.
