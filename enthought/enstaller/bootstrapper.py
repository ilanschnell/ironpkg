#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 5/14/2006
#------------------------------------------------------------------------------

import sys
import os
from os import path

from enthought.enstaller.api import \
     PYVER, IS_WINDOWS
from enthought.enstaller.easy_installer import \
     EasyInstaller


class Bootstrapper( EasyInstaller ) :
    """
    Derived from EasyInstaller, this class adds a bootstrap method which checks
    for setuptools and installs it if necessary.  From there, the standard
    EasyInstaller class is used to install the Enstaller egg.  This class knows
    to specify the extra requirement to easy_install if a GUI is specified.
    """

    setuptools_egg_name = "setuptools-(.*)-py%s\.egg$" % PYVER

    
    def __init__( self, find_links, gui, *args, **kwargs ) :

        """
        Construct with basic information on how to install Enstaller (where are
        the eggs: find_links, need a GUI?: gui)
        """
        super( Bootstrapper, self ).__init__( *args, **kwargs )

        self.gui = gui
        #
        # Remove all "file://" strings from the URLs since easy_install
        # cannot handle them.
        #
        self.find_links = []
        for url in find_links :
            if( url.lower().startswith( "file://" ) ) :
                url = url[7:]
                if( IS_WINDOWS ) :
                    url = url.strip( "/" )

            self.find_links.append( url )


    def bootstrap( self, install_dir, egg ) :
        """
        Bootstraps the entire app by installing the (assumed to be) Enstaller
        egg to the install_dir (or site-packages if not specified).  This also
        installs all dependencies listed in the egg by downloading them from the
        ordered list of URLs in find_links.  If gui is True, additional
        dependencies will be installed to support the Enstaller GUI.
        """
        #
        # Install setuptools if necessary, then call the EasyInstaller install.
        #
        self._assure_setuptools( install_dir )

        install_src = egg
        package_name = ""
        if( "-" in egg ) :
            (package_name, version) = path.basename( egg ).split( "-" )[0:2]
        tmp_repo = ""

        #
        # Call the method to enstall an Enstaller package (puts dependencies in
        # a separate subdir).
        #
        self._enstaller_install( install_dir, egg, self.gui )
        
        #
        # if the temp dir was added, remove it from the list of repos
        #
        if( tmp_repo != "" ) :
            self.find_links.remove( tmp_repo )


    def install( self, install_dir, egg ) :
        """
        Since bootstrapping requires installing AND importing afterwards, a
        standard install step is not adequate...in addition, the new package
        has to be seen by the interpreter, meaning the .pth file must be reread.
        """
        new_dists = super( Bootstrapper, self )._install( install_dir, egg )
        #
        # make the new package(s) visible to this interpreter
        #
        self._reread_easy_install_pth()

        return new_dists


    #############################################################################
    # Protected interface.
    #############################################################################

    def _assure_setuptools( self, install_dir ) :
        """
        Assures that setuptools is importable (by downloading and installing it
        if necessary).
        """
        try :
            import setuptools
            self.debug( "Found setuptools: %s\n" % str( setuptools ) )
            
        except ImportError, err :
            
            self.log( "Installing setuptools...\n" )

            #
            # find a compatible setuptools egg
            #
            self.debug( "Looking for a setuptools egg...\n" )
            url = self.downloader.find_latest_version( self.find_links,
                                                       self.setuptools_egg_name )
            if( url is None ) :
                msg = "Could not find a suitable setuptools egg " + \
                      "for Python %s!" % PYVER
                self.log( msg + "\n" )
                raise AssertionError, msg

            #
            # download the egg and run its "main", directing it to install
            # itself using the same options Enstaller is using.
            #
            cache = self.downloader.make_cache()
            egg = self.downloader.download_file( url, cache )

            orig_mods = sys.modules.keys()
            sys.path.insert( 0, egg )

            #
            # now that setuptools is available to the interpreter (via the egg
            # downloaded to the temp dir), have the install method (on the
            # EasyInstaller superclass) install it, then read the .pth file so
            # it can be imported.
            #
            self.install( install_dir, egg )
            
            #
            # remove the temporary egg and "unimport it" from the path so future
            # imports dont use it (it will probably go away soon)
            #
            sys.path.remove( egg )
            allmods = sys.modules.keys()
            for mod_name in allmods :
                if( not( mod_name in orig_mods ) ) :
                    del sys.modules[mod_name]
                    
    
