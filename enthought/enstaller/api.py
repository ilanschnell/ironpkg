#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007/02/07
#------------------------------------------------------------------------------

import sys
from os import path

#
# Version number is from the egg/setuptools
#
# ...this is a hack...since the package is named differently depending on if
# it is the bundled standalone app egg or the library module, the require()
# call must be different...use the path to this file to try and determine which
# egg must be required.
#
is_standalone_app = path.basename( path.dirname( path.dirname(
    path.dirname( __file__ ) ) ) ).startswith( "enstaller-" )

if( is_standalone_app ) :
    package_name = "enstaller"
else :
    package_name = "enthought.enstaller"

from pkg_resources import require
__version__ = require( package_name )[0].version

PYVER = "%s.%s" % (sys.version_info[0], sys.version_info[1])
IS_WINDOWS = sys.platform.lower().startswith( "win" )

#
# The default repository
#
ENTHOUGHT_REPO = "http://code.enthought.com/enstaller/eggs"


def get_version_string() :
    """
    Returns the version string for this package.
    """
    return "version %s" % __version__


def get_app_version_string() :
    """
    Returns the version string used in the Enstaller standalone app.
    """
    ver_str = "enstaller - %s on Python %s\n" % (get_version_string(), PYVER)

    return ver_str

