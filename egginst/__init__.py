"""
This is the API for egginst
===========================

More text here...


Egginst class
-------------

Is instantiated by an argument ARG (see below) and an optional verbose
keyword argument and has the following methods (for public use):

install():
    Installs the egg, provided by ARG, into the current Python environment

remove():
    Remove an installed package.  The ARG may be:
       * the full path of the egg which was used during the install
       * the egg name
       * or simply the project name


Functions:
----------

get_installed(prefix):
    Generator returns a sorted list of all installed packages.
    Each element is the filename of the egg which was used to install the
    package.
"""
from egginst.main import EggInst, get_installed, name_version_fn
