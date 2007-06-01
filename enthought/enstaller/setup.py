#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
#------------------------------------------------------------------------------
#
# setup.py used to build the enstaller egg
#

import sys
import glob
from os import path
import setuptools

from enstaller.api import version


def configuration( parent_package="", top_path=None ) :
    
    from numpy.distutils.misc_util import Configuration

    config = Configuration( "enstaller", parent_package, top_path )
    config.set_options( ignore_setup_xxx_py=True,
                        assume_default_configuration=True,
                        delegate_options_to_subpackages=True,
                        quiet=True )

    config.add_data_files( "images/*.png" )
    config.add_data_files( "images/*.gif" )
    config.add_data_files( "images/*.ico" )

    config.add_data_files( "LICENSE.txt" )
    config.add_data_files( "Enstaller_Help.html" )

    if( sys.platform.lower().startswith( "win" ) ) :
        config.add_subpackage( "wininst" )
    
    return config


#
# define the dependencies for Enstaller, including optional GUI deps
#
dependencies = ["enthought.traits>=1.1.0_r10704",
                "enthought.pyface>=1.1.1",
                "enthought.ets>=1.1.0_r10605",
                ]

extras_dependencies = {
    "GUI_win"   : ["numpy",
                   "enthought.traits[wx]>=1.1.0_r10704",
                   ],
    
    "GUI_linux" : ["numpy",
                   "enthought.traits[wx]>=1.1.0_r10704",
                   "wxPython2.6_gtk2_ansi",
                   "chrpath",
                   ],
    }

                
#
# simple setup() call
#
if __name__ == "__main__":
    from numpy.distutils.core import setup
    
    setup( version          = version,
           description      = "Enthought Installer",
           author           = "Enthought, Inc",
           author_email     = "info@enthought.com",
           url              = "http://code.enthought.com",
           license          = "BSD",
           install_requires = dependencies,
           extras_require   = extras_dependencies,
           zip_safe         = False,
           configuration    = configuration )
