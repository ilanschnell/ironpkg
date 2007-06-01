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

#
# Revision number is from SVN
#
revision = "$Rev$"[6:-2]

#
# Version number is from the egg/setuptools
#
from pkg_resources import require
__version__ = require( "enthought.enstaller" )[0].version


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
    return "version %s rev. %s" % (__version__, revision)


def get_app_version_string() :
    """
    Returns the version string used in the Enstaller standalone app.
    """
    ver_str = "enstaller - %s on Python %s\n" % (get_version_string(), PYVER)

    return ver_str

