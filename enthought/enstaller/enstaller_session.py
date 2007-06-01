#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007-02-15
#------------------------------------------------------------------------------

import sys
import types
import re
from os import path

#
# import this here, before any traits imports...
# Eventhought its not used in this module, it is in other modules which are
# imported later.  It must be imported before traits since it loads the expat
# system library, and since wx has its own copy of expat, a seg fault will
# result if the system''s expat is incompatible with wx''s expat...older system
# expat versions do not seem to bother wx, but a wx expat version which is newer
# than the system''s will cause problems (seg fault) with xmlrpclib...so, load
# whatever xmlrpclib wants first.
#
import xmlrpclib

from enthought.traits.api import \
     Trait, HasTraits, Str, List, Instance, Property

from enthought.enstaller.enstaller_traits import \
     CreatableDir, Url
from enthought.enstaller.api import \
     IS_WINDOWS
from enthought.enstaller.text_io import \
     TextIO
from enthought.enstaller.downloader import \
     Downloader
from enthought.enstaller.local_repository import \
     LocalRepository
from enthought.enstaller.repository import \
     Repository
from enthought.enstaller.enstaller_engine import \
     EnstallerEngine
from enthought.enstaller.preference_manager import \
     PreferenceManager
from enthought.enstaller.eula_manager import \
     EULAManager
from enthought.enstaller.repository_factory import \
     create_repository

version_cmp = Downloader.version_cmp


class EnstallerSession( HasTraits, TextIO ) :
    """
    Class containing the high-level APIs for all Enstaller operations.
    Instances of this class are used in the Enstaller GUI and CLI as well as
    other scripts/apps that need Enstaller functionality.
    """

    #
    # The directory where new packages will be installed.
    # This directory may or may not be in sys.path but will be created if it
    # does not exists as soon as this var is assigned to.
    #
    install_dir = CreatableDir( abspath=True, create=True )

    #
    # A list of URLs (local or remote) used to look for packages.
    # URLs earlier in the list have precedence over later ones.
    #
    find_links = Property
    _find_links = List( Url )

    #
    # A list of URLs that were rejected (usually from the preference_manager).
    # This is kept to prevent user from being warned repeatedly (cannot remove
    # invalids from pref manager since user may want to keep them in pref. file,
    # or see them in pref manager dialog.
    #
    _rejected_urls = List( Str )
    
    #
    # The url of a page easy_install uses as the Python Package Index.
    # By default, easy_install uses http://python.org/pypi when index_url = None
    #
    index_url = Trait( None, None, Url )

    #
    # The list of local repositories available to a Python interpreter, used
    # for listing, upgrading, de/activating, and installing packages to.
    # These repositories are initially sys.path plus any additional install_dirs
    # specified throughout the lifetime of the session.
    #
    pythonpath = List( LocalRepository )

    #
    # The list of repositories used for showing and retrieving available
    # packages. The packages in these repositories are not available to an
    # interpreter.
    #
    repositories = List( Repository )

    #
    # The EULA manager instance, used for checking that a remote repository''s
    # EULA has been agreed to by the user.  This agreement must be made prior to
    # accessing the repo (for downloading or browsing packages) if 1.) the repo
    # has a EULA, and 2.) the user has not agreed to the EULA in the past.
    #
    eula_manager = Instance( EULAManager )
    
    #
    # The object which is responsible for performing the core "actions" for
    # Enstaller, such as installing, removing, activating, upgrading, etc.
    # Note: the ', ()' means construct an instance by default instead of None.
    #
    engine = Instance( EnstallerEngine )

    #
    # Object which stores settings read in from user config file(s)
    #
    preferences = Instance( PreferenceManager, () )


    def __init__( self, **kwargs ) :
        """
        Required to be called with non-Traits TextIO args and have them set
        properly.  Also sets TextIO attrs with defaults.
        """

        self.verbose = kwargs.pop( "verbose", False )
        self.prompting = kwargs.pop( "prompting", True )
        self.logging_handle = kwargs.pop( "logging_handle", sys.stdout )

        super( EnstallerSession, self ).__init__( **kwargs )

    
    def initialize( self ) :
        """
        Perform various initialization operations.
        """

        self._read_preferences()
        self.read_pythonpath()
        self._add_install_dir()
        self._init_for_windows()
        

    def activate( self, package_objs ) :
        """
        Activates the packages passed in.  If a package is already active, a
        message is printed and it is skipped.
        """

        self._change_active_state( package_objs, action="activate" )


    def add_pythonpath_dir( self, repo_path ) :
        """
        Adds the repo object built from scanning repo_path to the list of local
        repos on the pythonpath.
        This is used primarily when an install dir is specified that was not on
        the original pythonpath.
        """

        added = False
        if( repo_path != "" ) :
            if( not( self.is_on_pythonpath( repo_path ) ) ) :
                repo = LocalRepository( location=repo_path,
                                        verbose=self.verbose,
                                        prompting=self.prompting,
                                        logging_handle=self.logging_handle )

                repo.build_package_list()
                self.pythonpath.insert( 0, repo )
                added = True

        return added


    def agree_to_url_eulas( self, urls ) :
        """
        Tells the EULAManager that the user has agreed to all of the EULAs in the
        list of URLs passed in.  The EULAManager will not require that the user
        agree to these EULAs again for all future sessions unless they change.
        """

        self.eula_manager.agree_to_url_eulas( urls )
        

    def check_eulas( self ) :
        """
        Calls the EULAManager to check that the user has agreed to any/all EULAs
        for the repositories in find_links.
        """

        pref_mgr_links = self._get_valid_unchecked_urls(
                             self.preferences.find_links.value )

        self.eula_manager.urls = self._find_links + pref_mgr_links

        return self.eula_manager.get_new_eulas()


    def deactivate( self, package_objs ) :
        """
        Deactivates the packages passed in.  If a package is already
        deactivated, a message is printed and it is skipped.
        """
        self._change_active_state( package_objs, action="deactivate" )


    def get_installed_packages( self, package_specs=[] ) :
        """
        Returns a list of packages in self.pythonpath which match package_specs.
        Returns all packages if no package_specs given.
        """

        pkg_list = []
        for repo in self.pythonpath :
            pkg_list += repo.find_packages( package_specs )

        return pkg_list


    def get_repository_packages( self, package_specs=[] ) :
        """
        Returns a list of packages from the repositories (not pythonpath repos)
        specified which match the package_specs given.  If no package_specs are
        given, all are returned.
        """

        pkg_list = []
        for repo in self.repositories :
            pkg_list += repo.find_packages( package_specs )

        return pkg_list


    def get_upgrade_packages( self, package_specs=[] ) :
        """
        Returns a list of package objects from the repositories that match the
        package specs and are upgrade versions (higher versions, the highest
        available) to the packages installed.
        """

        upgrades = []

        #
        # Create lists of the highest version of each package available from
        # the repos (matching package_specs) and of all installed.
        #
        repo_pkgs = self._get_highest_versions(
                        self.get_repository_packages( package_specs ) )

        installed_pkgs = self._get_highest_versions(
                             self.get_installed_packages() )

        #
        # Put all of the installed packages in a dict with the name as key
        # for easy lookup.
        #
        installed_pkgs_dict = {}
        for pkg in installed_pkgs :
            installed_pkgs_dict[pkg.name] = pkg

        #
        # For each of the highest-version packages returned from the query on
        # the repos, check if there is a package with the same name installed
        # and if it has a higher version than the installed one and add it to
        # the list of upgrades if so.
        #
        for pkg in repo_pkgs :

            if( installed_pkgs_dict.has_key( pkg.name ) and
                (version_cmp( pkg.version,
                              installed_pkgs_dict[pkg.name].version ) == 1) ) :

                upgrades.append( pkg )

        return upgrades
    

    def install( self, package_specs ) :
        """
        Calls the EnstallerEngine to install the packages specified in
        package_specs.
        """

        #
        # Set the preferences on the engine to those in the pref manager.
        #
        self._set_engine_preferences()
        
        new_egg_paths = self.engine.install( self.install_dir, package_specs )

        #
        # Have the target repo(s) rescan to find the newly-installed packages
        # and make a list of new package objects to return
        #
        new_pkg_list = []
        for (egg_dir, egg_fullname) in [path.split( p ) for p in new_egg_paths] :
            #
            # Find the repo obj for the new egg (should be present since the
            # install_dir is always added to self.pythonpath).
            #
            repo = self._find_local_repo( egg_dir )
            if( not( repo is None ) ) :
                #
                # Have the repo rebuild its list of packages, then find the
                # package that matches the egg name.
                #
                repo.build_package_list()

                for pkg in repo.packages :
                    if( pkg.fullname == egg_fullname ) :
                        new_pkg_list.append( pkg )
                        break

        return new_pkg_list


    def is_on_pythonpath( self, dirname ) :
        """
        Returns True if the dirname is already a local repo on self.pythonpath,
        False otherwise.
        """

        on_pythonpath = False
        dirpath = path.normcase( path.normpath( path.abspath( dirname ) ) )

        if( dirpath in [r.location for r in self.pythonpath] ) :
            on_pythonpath = True

        return on_pythonpath
        

    def read_pythonpath( self ) :
        """
        Populates the self.pythonpath list with Repository objects, one per
        directory on sys.path.

        Note: egg directories in sys.path are not included
        """

        #
        # Fixup the path so it is useable as a list of dirs to install to.
        #
        pythonpath = self._remove_eggs_from_path( sys.path, fix_names=True )
        pythonpath = self._remove_enstaller_deps_from_path( pythonpath )

        #
        # (re)build the list of repositories on sys.path
        #
        self.pythonpath = []

        for dirname in pythonpath :
            #
            # Do not process dirs which dont exist
            #
            if( path.exists( dirname ) ) :
                #
                # Create a repo obj and add only if not already present
                #
                if( not( self.is_on_pythonpath( dirname ) ) ) :
                    repo = LocalRepository( location=dirname,
                                            verbose=self.verbose,
                                            prompting=self.prompting,
                                            logging_handle=self.logging_handle )

                    self.debug( "Reading %s..." % dirname )
                    repo.build_package_list()
                    self.debug( "done.\n" )
                    self.pythonpath.append( repo )


    def read_repositories( self, repositories=[] ) :
        """
        Reads the package repos (not pythonpath repos) and builds the list of
        repo objects for future processing.  If no repositories are specified,
        all repos in find_links are read.
        """

        find_links = self.find_links
        
        if( repositories == [] ) :
            repositories = find_links
        else :
            for repo in repositories :
                # Do not support repos that are not in find_links for now.
                if( not( repo in find_links ) ) :
                    raise AssertionError, "all repos must be in find_links"
        #
        # (re)build the list of repositories
        #
        self.repositories = []

        for url in repositories :
            processed_urls = [r.location for r in self.repositories]
            #
            # Create a repo obj and add only if not already present
            #
            if( not( url in processed_urls ) ) :
                repo = create_repository( url,
                                          verbose=self.verbose,
                                          prompting=self.prompting,
                                          logging_handle=self.logging_handle )
                if( repo is None ) :
                    self.log( "Warning: Could not access repository at: " + \
                              "%s...skipping.\n" % url )
                else :
                    self.log( "Reading %s..." % url )
                    repo.build_package_list()
                    self.log( "done.\n" )
                    self.repositories.append( repo )


    def remove( self, package_objs ) :
        """
        Calls the EnstallerEngine to remove the packages referenced by
        package_objs, then removes the package object from the repo it is
        in.  Returns 0 on success, non-zero on first failure.
        """

        retcode = 0

        if( type( package_objs ) != types.ListType ) :
            package_objs = [package_objs]
            
        for pkg in package_objs :
            retcode = self.engine.remove( pkg ) or retcode
            repo = pkg.repository
            if( not( repo is None ) ) :
                repo.packages.remove( pkg )

        return retcode


    def toggle_active_state( self, package_objs ) :
        """
        Calls change_active_state() to toggle all packages.
        """

        self._change_active_state( package_objs )

        
    #############################################################################
    # Protected interface.
    #############################################################################

    def _add_install_dir( self ) :
        """
        Adds a LocalRepository for the install_dir to the beginning of
        self.pythonpath if it is not already in self.pythonpath.
        """

        self.add_pythonpath_dir( self.install_dir )


    change_state_actions = ["toggle", "activate", "deactivate"]
    change_state_messages = {"toggle" : "Toggling active state on",
                             "activate" : "Activating",
                             "deactivate" : "Deactivating", }
    
    def _change_active_state( self, package_objs, action="toggle" ) :
        """
        Action can be one of "toggle", which toggles the state of the packages,
        "activate" which activates if not already active, or "deactivate" which
        deactivate if not already deactivated.
        """

        if( not( action in self.change_state_actions ) ) :
            raise AssertionError, "action must be one of %s" \
                  % self.change_state_actions

        retcode = 0
        if( type( package_objs ) != types.ListType ) :
            package_objs = [package_objs]
        #
        # this has to be done through the package which calls its repository to
        # modify its pth file, once for each package (open, write, close pth
        # file for every package) since its not known if the same pth file is
        # used for every package (different install locations)...a better way
        # could be written, but...
        #
        for pkg in package_objs :
            if( (action == "activate") and pkg.active ) :
                self.log( "Package %s is already active...skipping.\n" \
                          % pkg.fullname )
                continue
            elif( (action == "deactivate") and not( pkg.active ) ) :
                self.log( "Package %s is already deactivated...skipping.\n" \
                          % pkg.fullname )
                continue
            else :
                orig_state = pkg.active
                
            self.log( "%s %s in %s..." % (self.change_state_messages[action],
                                          pkg.fullname, pkg.location) )
            pkg.toggle_active_state()
            #
            # Check
            #
            if( ((action == "activate") and not( pkg.active )) or
                ((action == "deactivate") and pkg.active) or
                ((action == "toggle") and (orig_state == pkg.active)) ) :
                self.log( "Error!\n" )
                retcode = 1
            else :
                self.log( "done.\n" )

        return retcode
    

    def _find_local_repo( self, dirname ) :
        """
        Returns the LocalRepository object for dirname in self.pythonpath.
        If an obj was not found, returns None.
        """

        retobj = None
        for repo in self.pythonpath :
            if( repo.location == dirname ) :
                retobj = repo
                break

        return retobj


    def _get_highest_versions( self, pkg_list ) :
        """
        Return a list of the highest version of each package in the list.
        The list will contain only one version per package name.
        """

        #
        # Create a sorted list of packages (see __cmp__ method in Package class)
        #
        plist = pkg_list[:]
        plist.sort()

        #
        # Remove repeats by iterating through the sorted list and adding
        # them to a dict with the package name as key.  The highest version
        # will be added last and therefore will be the only one mapped to
        # the package name key.
        #
        pkg_dict = {}
        for pkg in plist :
            pkg_dict[pkg.name] = pkg

        #
        # Return all the package objects in the dict.
        #
        return pkg_dict.values()


    def _get_valid_unchecked_urls( self, urls ) :
        """
        Returns a list of urls that do not contain local dirs that do not
        exist.  The list is built form the urls passed in.
        """
        
        valids = []
        invalids = []
        
        if( isinstance( urls, basestring ) ) :
            urls = [urls]
        #
        # Include all URLs from the preferences.
        #
        for url in urls :
            check = url.lower()
            #
            # If the dir starts with a remote protocol, add to list.
            #
            if( check.startswith( "http:" ) or
                check.startswith( "https:" ) or
                check.startswith( "ftp:" ) ) :
                valids.append( url )
            #
            # If the dir is a local file, check that it exists and is a dir.
            #
            else :
                if( check.startswith( "file://" ) ) :
                    check = check[7:]
                if( path.exists( check ) and path.isdir( check ) ) :
                    valids.append( url )

                else :
                    invalids.append( url )
        #
        # Warn about any links specified that were invalid (locals that DNE).
        #
        for url in invalids :
            if( not( url in self._rejected_urls ) ) :
                self.log( "Warning: %s does not exist...ignoring.\n" % url )
                self._rejected_urls.append( url )

        return valids

    
    def _init_for_windows( self ) :
        """
        Import wininst functions into the builtin module so post install scripts
        which check if they are being ran from a wininst installer and execute
        as if they were installed via the wininst installer.
        """

        if( IS_WINDOWS ) :
            self.debug( "Importing wininst api...\n" )
            try:
                import wininst.wininst as wininst
                sys.modules["__builtin__"].create_shortcut = \
                                              wininst.create_shortcut
                sys.modules["__builtin__"].directory_created = \
                                              wininst.directory_created
                sys.modules["__builtin__"].file_created = \
                                              wininst.file_created
                sys.modules["__builtin__"].get_root_hkey = \
                                              wininst.get_root_hkey
                sys.modules["__builtin__"].get_special_folder_path = \
                                              wininst.get_special_folder_path
                sys.modules["__builtin__"].message_box = wininst.message_box
                self.debug( "done.\n" )
                
            except ImportError, err :
                msg  = "Warning: wininst module could not be imported: %s" % err
                msg += "...some installs may not be complete.\n"
                self.log( msg )


    def _read_preferences( self ) :
        """
        Reads the various config files (many shared by setuptools and distutils)
        and loads the PreferenceManager instance with the relevant values.
        """

        self.preferences.read()


    def _remove_eggs_from_path( self, search_path, fix_names=False ) :
        """
        Returns a copy of search_path with all eggs (directories or zip files)
        removed.  Eggs are identified by the ".egg" extension in the name.
        If fix_names is True, the dir names in the path are made absolute.
        Note: files with a .zip extension are removed as well.
        """

        new_path = []
        for name in search_path :
            if( fix_names ) :
                name = path.normpath( path.abspath( name ) )
            if( not( path.splitext( name )[-1].lower() in [".egg", ".zip"] ) ) :
                new_path.append( name )

        return new_path


    def _remove_enstaller_deps_from_path( self, search_path ) :
        """
        Returns a copy of search_path with every directory path that is or is in
        enstaller_deps removed.
        """

        #
        # Heirarchy is like:
        # <install_dir>/enstaller-x.x.x-pyx.x.egg/enstaller/this_file
        # <install_dir>/enstaller_deps
        # ...if this package is not used in an installed egg, the new path
        # returned will be unchanged.
        #
        
        this_file = path.abspath( __file__ )
        this_package_dir = path.dirname( this_file )
        this_egg_dir = path.dirname( this_package_dir )
        this_egg_install_dir = path.dirname( this_egg_dir )
        enst_deps_dir = path.normcase( path.normpath(
            path.join( this_egg_install_dir, "enstaller_deps" ) ) )

        new_path = []
        for name in search_path :
            #
            # If the path in the searchpath does not start with the deps dir,
            # add it to the list to return.
            #
            norm_name = path.normcase( path.normpath( path.abspath( name ) ) )
            if( not( norm_name.startswith( enst_deps_dir ) ) ) :
                new_path.append( name )

        return new_path


    def _set_engine_preferences( self ) :
        """
        Sets the preferences on the EnstallerEngine to those in the pref manager.
        """

        self.engine.find_links = self.find_links
        self.engine.script_dir = (self.preferences.script_dir.value or None)
        self.engine.exclude_scripts = self.preferences.exclude_scripts.value
        self.engine.always_unzip = self.preferences.always_unzip.value
        self.engine.record = self.preferences.record.value


    #############################################################################
    # Traits handlers, defaults, etc.
    #############################################################################

    def _engine_default( self ) :
        """
        Return an instance of the EnstallerEngine to be used by default.
        """

        engine = EnstallerEngine( logging_handle=self.logging_handle,
                                  verbose=self.verbose,
                                  prompting=self.prompting )
        return engine


    def _eula_manager_default( self ) :
        """
        Return an instance of a EULAManager to be used by default.
        """

        eula_manager = EULAManager( logging_handle=self.logging_handle,
                                    verbose=self.verbose,
                                    prompting=self.prompting )
        return eula_manager


    def _get_find_links( self ) :
        """
        Getter for find_links...only returns find_links URLs that either do not
        have a EULA, or have EULAs that have been previously agreed to.

        A call to self.agree_to_url_eulas() is required to agree to any "new"
        EULAs.
        """

        find_links = []

        #
        # Get the new/rejected EULAs.
        # Strip any file:// off for checking...this should not be necessary.
        #
        new_eula_urls = []
        for url in self.check_eulas().keys() :
            if( re.match( "^file://", url, re.IGNORECASE ) ) :
                url = url[7:]
            new_eula_urls.append( url )

        pref_mgr_links = self._get_valid_unchecked_urls(
                             self.preferences.find_links.value )

        #
        # Iterate through each valid link and check the EULA state.
        #
        for url in self._find_links + pref_mgr_links :

            if( re.match( "^file://", url, re.IGNORECASE ) ) :
                url = url[7:]

            if( not( url in new_eula_urls ) ) :
                find_links.append( url )
            else :
                self.debug( "%s has a EULA that has not been agreed " % url + \
                            "to...will not use.\n" )
                
        return find_links


    def _install_dir_changed( self, old, new ) :
        """
        When the install_dir changes, it should be added to self.pythonpath
        """

        self._add_install_dir()
        

    def _set_find_links( self, find_links ) :
        """
        Set find_links.
        """

        self._find_links = self._get_valid_unchecked_urls( find_links )
