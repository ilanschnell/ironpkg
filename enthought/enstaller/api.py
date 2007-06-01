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

#
# The major.minor version of this package.  This must remain a float for easy
# comparison by other code.  This is used to check if the run_enstaller.py
# startup script is compatible with this package.
#
major_minor_version = 1.0
#
# version string: major.minor.micro and optional _<build or rev>
#
version = str( major_minor_version ) + ".0"
#
# Revision number is from SVN
#
revision = "$Rev$"[6:-2]

#
# Variables set by the launching script, run_enstaller.py (optional)
#
RUN_ENSTALLER_VERSION = None
RUN_ENSTALLER_REV = None


def get_version_string() :
    """
    Returns the version string for this package.
    """
    return "version %s rev. %s" % (version, revision)


def get_standalone_app_version_string() :
    """
    Returns the version string used in the Enstaller standalone app, which
    includes information about the launching script.
    """
    from enstaller.run_enstaller import PYVER
    ver_str = ""
    #
    # If run_enstaller.py was able to set these vars, use them...otherwise
    # do not attempt to report on the version info of the launch script.
    #
    if( not(RUN_ENSTALLER_VERSION is None) and not(RUN_ENSTALLER_REV is None) ) :
        ver_str = "\nrun_enstaller.py - version %s rev. %s\n" % \
                  (RUN_ENSTALLER_VERSION, RUN_ENSTALLER_REV)

    ver_str += "enstaller - %s on Python %s\n" % (get_version_string(), PYVER)

    return ver_str

