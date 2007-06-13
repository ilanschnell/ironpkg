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
import os
from os import path

from enthought.traits.api import \
     TraitError, HasTraits, Instance

from enthought.enstaller.text_io import \
     TextIO
from enthought.enstaller.downloader import \
     Downloader

from enthought.enstaller.session import Session


class CLI( HasTraits, TextIO ) :
    """
    The command-line interface to an Enstaller Session.
    """

    #
    # The underlying session object which the CLI manipulates
    #
    session = Instance( Session )


    def __init__( self, **kwargs ) :
        """
        Called with non-Traits TextIO args and uses them to set the TextIO
        attrs, or uses defaults if no args provided.
        """

        self.verbose = kwargs.pop( "verbose", False )
        self.prompting = kwargs.pop( "prompting", True )
        self.logging_handle = kwargs.pop( "logging_handle", sys.stdout )

        super( CLI, self ).__init__( **kwargs )


    def install( self, install_dir, package_specs ) :
        """
        Method for supporting the implicit install command.
        """

        #
        # Set the install dir on the session.
        #
        retcode = self._set_install_dir( install_dir )

        if( retcode == 0 ) :
            #
            # Make sure all relevant EULAs are agreed to before installing.
            #
            self._check_eulas()

            new_pkg_list = self.session.install( package_specs )
            output = self._get_installed_package_list_string( new_pkg_list )

            if( output != "" ) :
                self.log( "Successfully installed the following packages:\n" )
            self.log( output )

        return retcode
        
    
    def list_installed( self, package_specs=[] ) :
        """
        Method for supporting the "list_installed" command...logs a formatted
        string of packages matching package_specs, or all.
        """

        retcode = 0

        pkg_list = self.session.get_installed_packages( package_specs )
        output = self._get_installed_package_list_string( pkg_list )

        if( output == "" ) :
            pspecs = ", ".join( ["'%s'" % p for p in package_specs] )
            output = "No packages found matching: %s\n\nSearchpath is:\n%s\n" \
                     % (pspecs, self._get_path_string( format=True ))

        self.log( output )

        return retcode


    def list_repos( self, package_specs=[] ) :
        """
        Method for supporting the "list_repos" command...logs a formatted
        string of packages matching package_specs available from the repositories
        in find_links, or all of them.
        """

        retcode = 0

        #
        # Read the remote repos to build a list of packages.
        #
        self._read_repositories()
        
        pkg_list = self.session.get_repository_packages( package_specs )
        output = self._get_repos_package_list_string( pkg_list )

        if( output == "" ) :
            pspecs = ", ".join( ["'%s'" % p for p in package_specs] )
            output = "No packages found matching: %s\n\n" % pspecs + \
                     "Repositories searched:\n%s\n" \
                     % self._get_find_links_string( format=True )

        self.log( output )

        return retcode


    def list_upgrades( self, install_dir, package_specs ) :
        """
        Method for supporting the "list_upgrades" command...logs a formatted
        string of packages matching package_specs available from the repositories
        in find_links that upgrade installed packages.
        """

        retcode = 1

        #
        # Get a list of upgrade packages...None returned if an error occurred.
        #
        upgrades = self._get_upgrade_packages( install_dir, package_specs )

        if( not( upgrades is None ) ) :

            output = self._get_repos_package_list_string( upgrades )

            if( output != "" ) :
                self.log( "\nThe following upgrade packages are available:\n" )
                self.log( output )

            else :
                self.log( "\nNo upgrades were found...installed packages " + \
                          "are up-to-date.\n" )

            retcode = 0
            
        return retcode
        

    def remove( self, package_specs ) :
        """
        Removes the packages specified by the package_specs.
        """

        return self._process_packages( package_specs, "remove" )
        

    def upgrade( self, install_dir, package_specs ) :
        """
        Upgrades the packages specified by the package_specs, or all installed
        packages, if upgrades are available.
        """

        retcode = 1
        
        #
        # Get a list of upgrade packages...None returned if an error occurred.
        #
        upgrades = self._get_upgrade_packages( install_dir, package_specs )

        self.debug( "The following upgrades were found:\n%s\n" % \
                    self._get_repos_package_list_string( upgrades ) )
        
        if( not( upgrades is None ) ) :

            new_pkg_list = []

            if( len( upgrades ) > 0 ) :
                #
                # Install the packages, output the results.
                #
                new_pkg_list = self.session.install( upgrades )
                output = self._get_installed_package_list_string( new_pkg_list )

                if( output != "" ) :
                    self.log( "\nSuccessfully installed the following " + \
                              "packages:\n" )
                    self.log( output )

            #
            # If nothing was found to upgrade, or nothing was installed...
            #
            if( len( new_pkg_list ) == 0 ) :
                self.log( "\nNo upgrades were found...installed packages " + \
                          "are up-to-date.\n" )

            retcode = 0
            
        return retcode


    def activate( self, package_specs ) :
        """
        Activates the packages specified by the package_specs.
        """

        return self._process_packages( package_specs, "activate" )


    def deactivate( self, package_specs ) :
        """
        Deactivates the packages specified by the package_specs.
        """

        return self._process_packages( package_specs, "deactivate" )


    #############################################################################
    # Protected interface.
    #############################################################################

    def _check_eulas( self ) :
        """
        Prompts the user with any/all EULAs from the URLs in the session
        find_links that have not been agreed to.
        """

        new_agreed_eula_urls = []
        #
        # Get the "new" (newly found or updated) EULAs...this will be empty
        # on repeated calls to the same list of URLs with EULAs that dont change.
        #
        new_eula_dict = self.session.check_eulas()

        for (url, eula) in new_eula_dict.items() :
            msg  = "\n" + "=" * 60 + "\n"
            msg += "New/updated End User License Agreement for:\n%s\n" % url
            msg += "-" * 60 + "\n"
            msg += eula
            msg += "-" * 60 + "\n"
            msg += "Do you agree to the terms of the EULA for\n%s? (y/n) " % url
            if( self.prompt( msg, False ) ) :
                new_agreed_eula_urls.append( url )

        if( len( new_agreed_eula_urls ) > 0 ) :
            self.session.agree_to_url_eulas( new_agreed_eula_urls )
            

    def _get_find_links_string( self, format=True ) :
        """
        Returns the string rep. of self.find_links.
        If format=True, add newlines.
        """

        retstring = ""
        urls = self.session.find_links

        if( len( urls ) > 0 ) :
            if( format ) :
                retstring = "\n".join( urls )
            else :
                retstring = os.pathsep.join( urls )

        return retstring


    def _get_max_package_string_lengths( self, package_list ) :
        """
        Returns the longest package name, version string, and location string
        lengths from the list of packages for use in formatting a table of
        packages with properly-sized columns, so everything lines up nicely.
        """

        #
        # find the longest name and ver string for formatting
        #
        longest_name = len( "name" )
        longest_ver = len( "version" )
        longest_loc = len( "location" )
        
        for pkg in package_list :
            namelen = len( pkg.name )
            if( namelen > longest_name ) :
                longest_name = namelen
            verlen = len( pkg.version )
            if( verlen > longest_ver ) :
                longest_ver = verlen
            loclen = len( pkg.location )
            if( loclen > longest_loc ) :
                longest_loc = loclen
        #
        # Add one for space
        #
        longest_name += 1
        longest_ver += 1
        longest_loc += 1

        return (longest_name, longest_ver, longest_loc)

    
    def _get_next_package_to_process( self, pkg_list, action ) :
        """
        Returns the first package in the list, unless one or more other packages
        with the same fullname exist in the list.  If >1, the user is prompted
        to pick the package they intend to perform the operation on.
        Upon return, pkg_list will have all instances of packages which match
        the last package (as returned by pop()) removed.
        Action is just for prompting and indicates to the user what operation
        they are being prompted to pick a package for.
        """

        pkg = pkg_list.pop()
        matching_packages = []
        #
        # Build a list of matching packages, removing matches from the original
        # list as matches are found (this means only one removal per mathcing
        # set can be done at a time).
        #
        for p in pkg_list[:] :
            if( p.fullname == pkg.fullname ) :
                matching_packages.append( p )
                pkg_list.remove( p )
        #
        # If matches were found, prompt the user for the package (by number).
        # If prompting is off, default to the first match.
        #
        if( len( matching_packages ) ) :
            #
            # Make a complete list of all matches the create a message string.
            #
            all_pkgs = [pkg] + matching_packages
            msg = "Multiple packages named %s were found.\n" % pkg.fullname
            
            for i in range( len( all_pkgs ) ) :
                p = all_pkgs[i]
                msg += " %s.) %s\n" % (i, path.join( p.location, p.fullname ) )
            msg += "Enter the number next to the package to %s : " % action
            #
            # Prompt the user until a valid answer is given.
            #
            index = -1
            while( not( index in range( len( all_pkgs ) ) ) ) :
                index = self.prompt( msg, 0 )

            pkg = all_pkgs[index]

        return pkg
        

    def _get_installed_package_list_string( self, package_list ) :
        """
        Given a list of installed package objects, returns a string repr of
        the list.
        """

        retstring = ""
        #
        # Get the sizes of the longest strings for the variable-sized columns.
        #
        (longest_name, longest_ver, longest_loc) = \
                       self._get_max_package_string_lengths( package_list )
        
        #
        # format the string
        #
        if( len( package_list ) ) :
            #
            # if packages found, create a header first
            #
            line_len = min( 60, (longest_name + 2 + longest_ver +
                                 3 + longest_loc + 1) )
            retstring  = "-" * line_len
            retstring += "\n"
            retstring += "name%s| " % (" " * (longest_name - 4))
            retstring += "version%s| " % (" " * (longest_ver - 7))
            retstring += "act | "
            retstring += "location\n"
            retstring += "%s\n" % ("-" * line_len)
            #
            # add a line of package info for each package
            #
            for pkg in package_list :
                active = "Y"

                if( pkg.name in ["enstaller", "enstaller.gui"] ) :
                    active = " "
                elif( not( pkg.active ) ) :
                    active = "n"
                    
                retstring += "%s%s| " % (pkg.name,
                                         " " * (longest_name - len( pkg.name )))
                retstring += "%s%s| " % (pkg.version,
                                         " " * (longest_ver - len( pkg.version)))
                retstring += " %s  | " % active
                retstring += "%s\n" % pkg.location
            
        return retstring
        

    def _get_path_string( self, format=True ) :
        """
        Returns the string rep. of self.pythonpath.
        If format=True, add newlines.
        """

        retstring = ""
        dirs = [repo.location for repo in self.session.pythonpath]

        if( len( dirs ) > 0 ) :
            if( format ) :
                retstring = "\n".join( dirs )
            else :
                retstring = os.pathsep.join( dirs )

        return retstring


    def _get_repos_package_list_string( self, package_list ) :
        """
        Given a list of repository package objects, returns a string repr of
        the list.
        """

        retstring = ""
        #
        # Get the sizes of the longest strings for the variable-sized columns.
        #
        (longest_name, longest_ver, longest_loc) = \
                       self._get_max_package_string_lengths( package_list )

        #
        # Get the list of installed packages for indicating if any of the
        # available packages are already installed.
        #
        installed_packages = self.session.get_installed_packages()
        
        #
        # format the string
        #
        if( len( package_list ) ) :
            #
            # if packages found, create a header first
            #
            line_len = min( 60, (longest_name + 2 + longest_ver +
                                 3 + longest_loc + 1) )
            retstring  = "-" * line_len
            retstring += "\n"
            retstring += "name%s| " % (" " * (longest_name - 4))
            retstring += "version%s| " % (" " * (longest_ver - 7))
            retstring += "inst | "
            retstring += "location\n"
            retstring += "%s\n" % ("-" * line_len)
            #
            # add a line of package info for each package
            #
            for pkg in package_list :
                installed = "n"
                if( pkg in installed_packages ) :
                    installed = "Y"
                    
                retstring += "%s%s| " % (pkg.name,
                                         " " * (longest_name - len( pkg.name )))
                retstring += "%s%s| " % (pkg.version,
                                         " " * (longest_ver - len( pkg.version)))
                retstring += "  %s  | " % installed
                retstring += "%s\n" % pkg.location
            
        return retstring


    def _get_upgrade_packages( self, install_dir, package_specs ) :
        """
        Return a list of package objects matching package_specs (or all)
        that will upgrade installed packages.
        """

        #
        # If this is returned, an error occurred
        #
        upgrades = None
        
        #
        # Set the install dir where the upgrades will be installed to.
        # Do this before creating the list of upgrade packages so the install
        # dir is included when looking for packages already installed.
        #
        retcode = self._set_install_dir( install_dir )

        if( retcode == 0 ) :
            #
            # Read the remote repos to build a list of packages available for
            # install.
            #
            self._read_repositories()

            #
            # Get a list of packages that are upgrades to the installed ones (if
            # no package_specs given, look for upgrades for all installed pkgs).
            #
            upgrades = self.session.get_upgrade_packages( package_specs )

        return upgrades


    installed_package_operations = ["activate", "deactivate", "remove"]
    
    def _process_packages( self, package_specs, action ) :
        """
        Perform the action on all packages matching package_specs.
        Action must be one of "activate", "deactivate", "remove".
        """

        if( not( action in self.installed_package_operations ) ) :
            raise AssertionError, "action must be one of %s" \
                  % self.installed_package_operations
        
        retcode = 0
        #
        # Get a list of package objects to operate on.
        #
        pkg_list = self.session.get_installed_packages( package_specs )

        if( len( pkg_list ) > 0 ) :
            #
            # Go through each until there are no more packages.
            # _get_next_package_to_process() uses pop(), which is why the list
            # is reversed.
            #
            pkg_list.reverse()
            while( len( pkg_list ) > 0 ) :

                pkg = self._get_next_package_to_process( pkg_list, action )
                #
                # Perform the requested operation.
                #
                if( action == "remove" ) :
                    rc = self.session.remove( pkg )
                elif( action == "activate" ) :
                    rc = self.session.activate( pkg )
                elif( action == "deactivate" ) :
                    rc = self.session.deactivate( pkg )
                    
                if( rc != 0 ) :
                    retcode = rc
        #
        # Print error if package_specs dont match any packages.
        #
        else :
            self.log( "Error: Did not find any packages matching: %s\n" \
                      % ", ".join( ["'%s'" % p for p in package_specs] ) )
            self.log( "\nSearchpath is:\n%s\n" \
                      % self._get_path_string( format=True ) )
            retcode = 1
            
        return retcode


    def _read_repositories( self ) :
        """
        Read the remote repositories to build a list of packages.
        """
        
        #
        # Make sure all relevant EULAs are agreed to before accessing the repos.
        #
        self._check_eulas()

        #
        # Read the repositories (this can be expensive, but since the current
        # CLI implementation only performs one operation per "session", it is
        # safe to do this every time this method is called).
        #
        self.session.read_repositories()


    def _set_install_dir( self, install_dir ) :
        """
        Sets the session install_dir which causes it to also scan that dir
        for packages already installed and add the directory to its pythonpath.
        Returns 0 on success, 1 if the dir cannot be an install dir.
        """

        retcode = 0
        
        try :
            self.session.install_dir = install_dir

        except TraitError, err :
            if( install_dir == Downloader.get_site_packages_dir() ) :
                self.log( "Error: The default install directory " + \
                          "%s cannot be used (cannot create " % install_dir + \
                          "files there).  Please specify an alternate " + \
                          "location using --install-dir (-d).\n" )
            else :
                self.log( "Error: Cannot create files in the specified " + \
                          "install directory: %s\n" % install_dir )
            retcode = 1

        return retcode
