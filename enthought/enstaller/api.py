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
import re
from os import path
import platform

from pkg_resources import \
     require, get_platform

################################################################################
# IMPORTANT!
# This module cannot import anything but standard library modules (and
# setuptools).  If this is violated, bootstrapping as well as "standalone" app
# Enstaller sessions could break.
################################################################################



###
# END of VARIABLES
####


PYVER = "%s.%s" % (sys.version_info[0], sys.version_info[1])
IS_WINDOWS = sys.platform.lower().startswith( "win" )

#
# Version number is from the egg/setuptools
#
# ...this is a hack...since the project is named differently depending on if
# its the bundled standalone app egg or the library packages, the require()
# call must be different...use the path to this file to try and determine which
# egg must be required.
#
is_standalone_app = path.basename( path.dirname( path.dirname(
    path.dirname( __file__ ) ) ) ).startswith( "enstaller-" )

if( is_standalone_app ) :
    package_name = "enstaller"
else :
    package_name = "enthought.enstaller"

__version__ = require( package_name )[0].version
version = __version__


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


################################################################################
#### Attempt to automatically detect the platform to use when accessing
#### code.enthought.com/enstaller/eggs
################################################################################
(PLAT, PLAT_VER) = platform.dist()[0:2]

#
# Map RedHat to Enthought repo names
#
if( PLAT.lower().startswith( "redhat" ) ) :
    PLAT = "rhel"
    if( PLAT_VER.startswith( "3" ) ) :
        PLAT_VER = "3"
    elif( PLAT_VER.startswith( "4" ) ) :
        PLAT_VER = "4"
    elif( PLAT_VER.startswith( "5" ) ) :
        PLAT_VER = "5"
#
# Ubuntu returns debian...check /etc/issue too
#
elif( PLAT.lower().startswith( "debian" ) ) :
    if( path.exists( "/etc/issue" ) ) :
        fh = open( "/etc/issue", "r" )
        lines = fh.readlines()
        fh.close()
        patt = re.compile( "^([\w]+) ([\w\.]+).*" )
        for line in lines :
            match = patt.match( line )
            if( not( match is None ) ) :
                plat = match.group( 1 ).lower()
                if( plat == "ubuntu" ) :
                    PLAT = plat
                    PLAT_VER = match.group( 2 ).lower()
            break
#
# Default to XP for now for Windows.
#
elif( IS_WINDOWS ) :
    PLAT = "windows"
    # Assume XP for now?
    PLAT_VER = "xp"
#
# setuptools get_platform() finds the right info for OSX
#
elif( sys.platform.lower().startswith( "darwin" ) ) :
    (PLAT, PLAT_VER) = get_platform().split( "-" )[0:2]


#
# warn the user if the detected platform may not be supported
#
supported = ["windows", "macosx", "debian", "rhel", "suse", "ubuntu"]

if( not( PLAT in supported ) or (PLAT_VER == "") ) :
    msg = """
    Warning: There may not be an Enthought repository for platform "%s" "%s".
    Check http://code.enthought.com/enstaller/eggs for the available platforms.
    """ % (PLAT, PLAT_VER)

    print msg


#
# The default repository, based on the platform name and version.
#
ENTHOUGHT_REPO = "http://code.enthought.com/enstaller/eggs/%s/%s" \
                 % (PLAT, PLAT_VER)

