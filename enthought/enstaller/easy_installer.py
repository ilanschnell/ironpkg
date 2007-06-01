#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007-02-12
#------------------------------------------------------------------------------

import sys
import os
import site
import types
import re
import shutil
from os import path
import warnings

from enthought.enstaller.api import \
     IS_WINDOWS
from enthought.enstaller.text_io import \
     TextIO
from enthought.enstaller.downloader import \
     Downloader
from enthought.enstaller.url_util import \
     URLUtil

#
# THIS MODULE CANNOT USE TRAITS SINCE IT IS USED FOR BOOTSTRAPPING.
#

#
# setuptools scans and re-arranges sys.path on import and prints warnings when
# it sees an egg present when the same module had already been imported.  This
# happens occasionally with Enstaller...it is harmless, so do not display it.
#
warnings.filterwarnings( "ignore", ".*Module enstaller .*", UserWarning )


class EasyInstaller( TextIO ) :
    """
    Class which interfaces with the easy_install command of setuptools.  This
    class also encapsulates some of the other initialization needed in order to
    better integrate easy_install into another application.
    """
    
    def __init__( self, *args, **kwargs ) :
        """
        Construct with optional flags for TextIO class.
        """
        super( EasyInstaller, self ).__init__( *args, **kwargs )

        #
        # setup a downloader using the same verbose, logging, etc. options
        #
        self.downloader = Downloader( *args, **kwargs )
        self.site_packages_dir = Downloader.get_site_packages_dir()

        #
        # default options to easy_install
        #
        self._install_dir = self.site_packages_dir
        self.find_links = []
        self.always_unzip = False
        self.no_deps = False
        self.script_dir = None
        self.index_url = None
        self.record = ""
        self.exclude_scripts = False
        
        #
        # A list for easy_install to populate with Distribution objects
        # representing the packages easy_install just installed (this list
        # is normally not returned by easy_install()
        #
        self.newly_installed_dists = []

        #
        # A dictionary mapping installed egg to the list of files that were
        # installed for it...this is normally lumped into a single "record"
        # file by easy_install.
        #
        self.newly_installed_files = {}
        
        #
        # Instance of a URLUtil used for accessing URLs with error handling.
        #
        self._urlutil = URLUtil( *args, **kwargs )


    def install( self, install_dir, package_spec ) :
        """
        Calls either the standard install() or one for installing Enstaller.
        If the package_spec is an enstaller egg, this call was most likely
        made as part of an upgrade attempt, since bootstrapping calls
        _enstaller_install() directly.
        """
        #
        # FIXME: If a GUI is not to be installed/updated, look for [NO_GUI]
        # in the spec.
        #
        if( isinstance( package_spec, basestring ) and
            ("[NO_GUI]" in package_spec) ) :
            gui = False
        else :
            gui = True
            
        #
        # Handle the case of a real file (like when bootstrapping or local repo)
        #
        if( path.exists( package_spec ) ) :

            package_file = path.basename( package_spec )

            if( package_file.split( "-" )[0].lower() == "enstaller" ) :
                return self._enstaller_install( install_dir, package_spec, gui )

        #
        # Handle a package spec
        #
        spec_name = re.split( "[\[\]\_\-\<\>\=]+", package_spec )[0].lower() 
        if( spec_name == "enstaller" ) :
            return self._enstaller_install( install_dir, package_spec, gui )

        #
        # Otherwise, perform a normal install
        #
        return self._install( install_dir, package_spec )


    #############################################################################
    # Protected interface.
    #############################################################################

    def _assure_install_dir( self ) :
        """
        Assures that the install_dir exists (by creating it if necessary) and
        that it is writable.  Raises AssertionError if necessary.
        """
        if( not( path.exists( self._install_dir ) ) ) :
            try :
                os.makedirs( self._install_dir )
            except OSError, err :
                msg = "Could not create the install dir: %s\n%s" \
                      % (self._install_dir, err)
                self.log( "\n%s\n" % msg )
                raise AssertionError, msg

        testfile = path.join( self._install_dir, "test" )
        try :
            f = open( testfile, "w" ).close()
        except IOError, err :
            msg = "Cannot create files in the install dir: %s\n%s" \
                  % (self._install_dir, err)

            self.log( "\n%s\n" % msg )
            raise AssertionError, msg
        try :
            os.remove( testfile )
        except :
            pass


    def _build_easy_install_arg_list( self, package_spec ) :
        """
        Returns a list of strings which are used as args to the easy_install
        "main" call, equivalent to calling it from the command-line.
        """
        ei_args = []
        
        if( self.verbose ) :
            ei_args += ["--verbose"]
        else :
            ei_args += ["--quiet"]

        if( self.record != "" ) :
            ei_args += ["--record=%s" % self.record]
            
        if( self.always_unzip ) :
            ei_args += ["--always-unzip"]

        if( self.exclude_scripts ) :
            ei_args += ["--exclude-scripts"]
            
        if( self.no_deps ) :
            ei_args += ["--no-deps"]
        #
        # If script_dir is specified in the preferences, use it
        # If script_dir is not specified, but install_dir is, then
        # setuptools will install scripts to install_dir, which is not
        # what we want.
        #
        if( not( self.script_dir is None ) ) :
            ei_args += ["--script-dir=%s" % self.script_dir]

        elif( not( self._install_dir is None ) ) :
            if sys.platform == 'win32':
                ei_args += ["--script-dir=%s" \
                            % os.path.join( sys.prefix, "Scripts" )]
            else:
                #
                # keep the scripts with the egg, the user may not have
                # permission to write to sys.prefix/bin where scripts
                # would normally go.
                #
                pass

        if( not( self.index_url is None ) ) :
            ei_args += ["--index-url=%s" % self.index_url]
            
        ei_args += ["--always-copy"]
        ei_args += ["--install-dir=%s" % self._install_dir]

        #
        # Fixup find_links...easy_install does not like file://c:\... or spaces
        #
        if( len( self.find_links ) > 0 ) :
            fl = [l.replace( "file://", "" ) for l in self.find_links]
            fl = [l.replace( " ", "\ " ) for l in fl]
            ei_args += ["--find-links=%s" % " ".join( fl )]

        ei_args += [package_spec]

        return ei_args
    

    def _build_easy_install_cmd_map( self ) :
        """
        Returns a mapping of the easy_install command to a custom command
        class which overrides specific functions with Enstaller utilities
        for a more integrated appearance and behavior.
        """
        from setuptools.package_index import PackageIndex
        from setuptools.command.easy_install import easy_install
        from pkg_resources import find_distributions
        
        download_file = self.downloader.download_file
        cache = self.downloader.make_cache()
        urlutil = self._urlutil
        
        #
        # Replace the download function in the PackageIndex class with
        # Enstallers, which shows the user a progress meter.
        #
        class EnstallerPackageIndex( PackageIndex ) :
            def _download_to( self, url, filename ) :
                #
                # Assume the file is always going to be in a temp dir, so
                # override easy_installs temp dir with Enstallers, allowing
                # it to be cached.
                #
                tmp_file = download_file( url, cache )
                #
                # Silly, but copy downloaded file to easy_installs tempdir.
                #
                shutil.copyfile( tmp_file, filename )
                u = urlutil.urlopen( url )
                if( u is None ) :
                    raise IOError, "Could not access %s" % url
                headers = u.info()
                return headers

        #
        # Reset some bookkeeping vars for information that Enstaller cares about
        #
        self.newly_installed_dists = []
        self.newly_installed_files = {}

        
        class enstaller_easy_install( easy_install ) :

            installed_files = {}
            installed_dists = []
            
            def __init__( self, *args, **kwargs ) :
                easy_install.__init__( self, *args, **kwargs )
                self.create_index = EnstallerPackageIndex


            def easy_install( self, *args, **kwargs ) :
                """
                Override here to set self.outputs to the complete list of all
                files installed from every package, since --record uses this.
                """
                retval = easy_install.easy_install( self, *args, **kwargs )

                self.outputs = []
                for values in self.installed_files.values() :
                    self.outputs += values

                return retval
            
                    
            def get_install_files_list( self, dist ) :
                """
                Returns the list mapped to the egg about to be installed which
                will be populated with files installed from the egg.
                """
                #
                # Get the full path to the install to use as a key
                #
                if( hasattr( dist, "location" ) ) :
                    egg = dist.location
                    dest = path.join( self.install_dir, path.basename( egg ) )

                else :
                    dest = dist

                return self.installed_files.setdefault( dest, [] )
            

            def install_eggs( self, *args, **kwargs ) :
                """
                Override to keep a list of the Distribution objects installed.
                """
                dists = easy_install.install_eggs( self, *args, **kwargs )
                self.installed_dists += dists
                return dists


            def install_item( self, spec, download, tmpdir,
                              deps, install_needed=False ) :
                """
                Override to work around --always-copy behavior: it normally
                ignores --no-deps when --always-copy is used, and --always-copy
                will not install a package if the source is a file on disk
                (intentional, but not desired for Enstaller).
                """

                # Installation is also needed if file in tmpdir or is not an egg
                install_needed = install_needed or \
                                 os.path.dirname(download) == tmpdir
                install_needed = install_needed or not download.endswith('.egg')

                if install_needed or self.always_copy:
                    #
                    # MOD: do not install if destination already exists
                    #
                    destination = path.join( self.install_dir,
                                             path.basename( download ) )

                    if( path.exists( destination ) ) :
                        dists = [self.egg_distribution( destination )]
                        #dists = [d for d in find_distributions( destination,
                        #                                        only=True )]
                    else :
                        # print is OK since setuptools log() does the same thing.
                        print "Processing %s" % os.path.basename(download)

                        #
                        # MOD: redirect the outputs and restore after.
                        #
                        self.outputs = self.get_install_files_list( destination )
                        dists = self.install_eggs(spec, download, tmpdir)

                    for dist in dists:
                        #
                        # MOD: if no deps, simply update the .pth,
                        # otherwise, process the dists normally.
                        #
                        if( self.no_deps ) :
                            self.update_pth( dist )

                        else :
                            #
                            # MOD: redirect the outputs and restore after.
                            #
                            self.outputs = self.get_install_files_list( dist )
                            self.process_distribution(spec, dist, deps)

                else:
                    dists = [self.check_conflicts(self.egg_distribution(download))]
                    #
                    # MOD: redirect the outputs and restore after.
                    #
                    self.outputs = self.get_install_files_list( dists[0] )
                    self.process_distribution(spec, dists[0], deps, "Using")

                if spec is not None:
                    for dist in dists:
                        if dist in spec:
                            return dist

        #
        # Set the bookkeeping vars in the override class to variables
        # accessible later by this class.
        #
        enstaller_easy_install.installed_dists = self.newly_installed_dists
        enstaller_easy_install.installed_files = self.newly_installed_files
        
        cmd_map = {"easy_install" : enstaller_easy_install}
        return cmd_map


    def _easy_install_log( self, msg ) :
        """
        Logs a message and prepends a tag to identify that it came from
        easy_install.
        """
        if( msg != "\n" ) :
            msg = "easy_install> %s" % msg.lstrip( "\n" )
        self.log( msg )


    def _enstaller_install( self, install_dir, package_spec, gui ) :
        """
        Called specifically to enstall or upgrade an Enstaller egg.
        This method installs Enstaller to the isntall dir, but installs all of
        its dependencies into a separate subdir of the install_dir.
        """

        #
        # Install the egg, but not the dependencies
        #
        self.no_deps = True

        new_dists = self._install( install_dir, package_spec )
        self._reread_easy_install_pth()

        self.no_deps = False

        #
        # Install all of the dependencies to the "enstaller_deps" subdir of
        # the install directory (a peer to the enstaller egg just installed).
        # ...assume it is safe to create a dir there (should be)
        #
        enstaller_deps_dir = path.join( self._install_dir, "enstaller_deps" )

        #
        # Scan a .pth file in here, in case it existed...this prevents packages
        # from being re-installed.
        #
        self._reread_easy_install_pth( enstaller_deps_dir )

        #
        # Save the installed files
        #
        installed_files = {}
        installed_files.update( self.newly_installed_files )
        
        #
        # Iterate through all the distributions just installed (should only be
        # one) and install their deps...this time, do not set no_deps.
        #
        return_dists = new_dists[:]
        
        for dist in new_dists :

            extras = []
            if( gui and (dist.key.lower() == "enstaller") ) :
                if( IS_WINDOWS ) :
                    extras = ["GUI_win"]
                else :
                    extras = ["GUI_linux"]

            for req in dist.requires( extras ) :

                req_str = "%s[%s]" % (req.key, ", ".join( req.extras ))
                specs = ["%s%s" % (op, vnum) for (op, vnum) in req.specs]
                req_str += ", ".join( specs )
                            
                return_dists += self._install( enstaller_deps_dir, req_str )
                installed_files.update( self.newly_installed_files )
                self._reread_easy_install_pth()

        #
        # Save the bookkepping vars just as if it were a regular install.
        #
        self.newly_installed_files = installed_files
        self.newly_installed_dists = return_dists
        
        return return_dists
        

    def _install( self, install_dir, package_spec ) :
        """
        Uses easy_install to install a package satisfying package_spec.
        """

        self.newly_installed_dists = []
        self.newly_installed_files = {}
        
        #
        # import this here so code like the bootstrapper can import this module
        # even if setuptools is not installed.
        #
        from setuptools.command.easy_install import main as easy_install

        self._set_install_dir( install_dir )
        #
        # use a custom easy_install command which overrides the standard
        # setuptools output mechanism...just because
        #
        cmd_map = self._build_easy_install_cmd_map()
        #
        # build the list of args to pass easy_install
        #
        ei_args = self._build_easy_install_arg_list( package_spec )
        #
        # easy_install uses print for logging...replace sys.stdout with
        # this class and setup methods to make it look like a file handle
        #
        orig_stdout = sys.stdout
        self.write = self._easy_install_log
        self.flush = self.logging_handle.flush
        sys.stdout = self
        #
        # call easy_install and catch all errors and have Enstaller report them
        #
        self.log( "Installing %s...\n" % package_spec )
        self.debug( "Calling easy_install with options: %s\n" % ei_args )
        try :
            easy_install( ei_args, cmdclass=cmd_map )

        except Exception, err :
            self.log( "Error installing %s: %s\n" % (package_spec, err) )
            del self.flush
            del self.write
            sys.stdout = orig_stdout
            raise
        #
        # return stdout and this class back to normal
        #
        sys.stdout = orig_stdout
        del self.flush
        del self.write

        #
        # Remove any install files from dists that were not just installed
        #
        new_dist_dirs = [d.location for d in self.newly_installed_dists]

        for files_dir in self.newly_installed_files.keys() :
            if( not( files_dir in new_dist_dirs ) ) :
                self.newly_installed_files.pop( files_dir )
                
        return self.newly_installed_dists


    def _reread_easy_install_pth( self, install_dir=None ) :
        """
        Add the newly-installed packages to the path for future imports by
        rescanning the updated easy_install.pth file.
        """
        install_dir = install_dir or self._install_dir
        try :
            # python 2.4
            site.addpackage( install_dir, "easy-install.pth", set( sys.path ) )
        except :
            # python 2.3
            site.addpackage( install_dir, "easy-install.pth" )


    def _set_install_dir( self, install_dir ) :
        """
        If an install dir was specified, set it so all future operations use it
        instead of the default (site-packages).  This method will also try to
        create the dir if it does not exist and/or check that it is writable.
        """
        if( (self._install_dir == "") or (install_dir != self._install_dir) ) :

            if( install_dir == "" ) :
                self._install_dir = self.site_packages_dir
            else :
                self._install_dir = path.normcase( path.abspath( install_dir ) )
            #
            # make sure install_dir exists (by creating if necessry) and writable
            #
            self._assure_install_dir()

            if( install_dir != self.site_packages_dir ) :
                if( not( install_dir in sys.path ) ) :
                    sys.path.insert( 0, install_dir )
                #
                # add install_dir to PYTHONPATH too
                #
                ppath = os.environ.get( "PYTHONPATH", "" )
                ppath_dirs = ppath.split( os.pathsep )
                if( not( install_dir in ppath_dirs ) ) :
                    os.environ["PYTHONPATH"] = install_dir
                    if( ppath ) :
                        os.environ["PYTHONPATH"] += os.pathsep + ppath
            #
            # windows style paths need to be double-escaped for regex operations
            #
            self._install_dir = self._install_dir.replace( "\\", "\\\\" )
