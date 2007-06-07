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

#
# DO NOT IMPORT API IN THE MODULE...it will cause a bootstrapping error since
# it makes pkg_resources calls
# 
import sys
import os
import tempfile
from os import path


from enthought.enstaller.easy_installer import \
     EasyInstaller

PYVER = "%s.%s" % (sys.version_info[0], sys.version_info[1])
IS_WINDOWS = sys.platform.lower().startswith( "win" )


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

        self.install( install_dir, egg )
        
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
        orig_find_links = self.find_links
        egg_spec = egg
        (egg_dir, full_egg_name) = path.split( egg )

        #
        # If the gui is to be installed, change the abs path to the egg to a
        # combination of an additional find_links and a package spec so the
        # "gui" extra can be specified.
        #
        if( (full_egg_name.lower().startswith( "enstaller" ) or
             full_egg_name.lower().startswith( "enthought.enstaller" )) and
            self.gui ) :
            try :
                (egg_name, egg_ver) = full_egg_name.split( "-" )[0:2]

            except :
                msg = "Unrecogonized egg name format: %s" % full_egg_name + \
                      "...expecting enstaller-<version>-<extra_tags>.egg"
                self.log( msg )
                raise AssertionError, msg

            self.find_links.insert( 0, egg_dir )
            egg_spec = "%s[gui]==%s" % (egg_name, egg_ver)
        
        #
        # Also, add -m (multi-version) so egg is not added to .pth file
        #
        new_dists = super( Bootstrapper, self ).install( install_dir,
                                                         egg_spec, "-m" )
        #
        # Run any post-installs for each new dist
        #
        for dist in new_dists :
            self._run_post_install( dist.location )
            
        #
        # make the new package(s) visible to this interpreter
        #
        self._reread_easy_install_pth()

        self.find_links = orig_find_links
        
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
                    
    
    def _run_post_install( self, installed_egg_path ) :
        """
        Run any post-install scripts in the newly-installed egg.
        """
        tmp_unpack_dir = ""
        #
        # if the egg installed is a dir, simply check the EGG-INFO subdir
        # for a post_install.py script and run it, otherwise, unzip it to
        # a temp location and do the same thing
        #
        if( path.isdir( installed_egg_path ) ) :
            egg_dir = installed_egg_path

        else :
            tmp_unpack_dir = tempfile.mkdtemp( prefix="enstaller-" )
            egg_dir = path.join( tmp_unpack_dir,
                                 path.basename( installed_egg_path ) )
            unpack_archive( installed_egg_path, egg_dir )
        #
        # check for post_install.py and run if present
        #
        pi_script = path.join( egg_dir, "EGG-INFO", "post_install.py" )
        if( path.exists( pi_script ) ) :

            try :
                execfile( pi_script, {"__file__" : pi_script} )
            except Exception, err :
                self.log( "Error: problem running post-install script %s: %s\n" \
                          % (pi_script, err) )

        #
        # cleanup if a temp extraction was done
        #
        if( tmp_unpack_dir != "" ) :
            self._rm_rf( tmp_unpack_dir )


    def _rm_rf( self, file_or_dir ) :
        """
        Removes the file or directory, returns 0 on success, 1 on failure.
        """
        retcode = 0
        try :
            if( path.exists( file_or_dir ) ) :
                if( path.isdir( file_or_dir ) ) :
                    shutil.rmtree( file_or_dir )
                else :
                    os.remove( file_or_dir )

        except (IOError, OSError), err :
            self.log( "Error: could not remove %s: %s\n" % (file_or_dir, err) )
            retcode = 1

        return retcode
