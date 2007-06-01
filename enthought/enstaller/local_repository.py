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
import glob
from types import ListType

from enthought.traits.api import \
     Str, Bool

from enthought.enstaller.api import \
     IS_WINDOWS
from repository import \
     Repository
from package import \
     Package, is_egg_installable



class LocalRepository( Repository ) :
    """
    A repository somewhere on a local disk.

    This can also be considered an installation location or a directory on a
    Python interpreters sys.path.  This class is often used for operations on
    the pth files contained in install location directories.
    """
    #
    # Traits for managing and creating pth files so the repository (directory)
    # can have its packages accessed by a Python interpreter.
    #
    _pth_file = Str
    _pth_header = Str( "import sys; sys.__plen = len(sys.path)" )
    _pth_footer = Str( "import sys; new=sys.path[sys.__plen:]; del sys.path[sys.__plen:]; p=getattr(sys,'__egginsert',0); sys.path[p:p]=new; sys.__egginsert = p+len(new)" )

    #
    # If on Windows, assume pth entries are all lowercase for comparisons.
    #
    _pth_lowercase_entries = IS_WINDOWS

    #
    # The pth file name...must be easy-install.pth for setuptools to recogonize.
    #
    _pth_filename = Str( "easy-install.pth" )

    
    def build_package_list( self ) :
        """
        finds all the packages in the local repository (directory) and builds
        the self.packages list with Packages objects
        """
        self.packages = []
        
        for egg_file in glob.glob( path.join( self.location, "*.egg" ) ) :

            p = Package( repository=self, egg_url=egg_file )
            #
            # set an info_url if info file present
            #
            info_file = egg_file + ".info"
            if( path.exists( info_file ) ) :
                p.info_url = info_file
                
            self.packages.append( p )

        Repository.build_package_list( self )


    def get_active_packages( self ) :
        """
        Returns the list of packages which are in the pth file, or [] if
        pth file DNE
        """
        active_packages = []
        pth_lines = self._get_pth_file_lines()
        #
        # extract only the package fullnames from the lines in the .pth file
        #
        if( self._pth_header in pth_lines ) :
            pth_lines.remove( self._pth_header )
        if( self._pth_footer in pth_lines ) :
            pth_lines.remove( self._pth_footer )
        #
        # lowercase compare on Windows
        #
        if( sys.platform.startswith( "win" ) ) :
            lower_for_compare = True
            pth_lines = [p.lower() for p in pth_lines]
        else :
            lower_for_compare = False
        #
        # add each package obj which matches the ones in the .pth to return list
        #
        for pkg in self.packages :
            if( lower_for_compare ) :
                pkg_name = pkg.fullname.lower()
            else :
                pkg_name = pkg.fullname

            if( pkg_name in pth_lines ) :
                active_packages.append( pkg )

        return active_packages
    

    def is_package_active( self, package_fullname ) :
        """
        This is used only in a LocalRepository, since all others dont
        have pth files (in this case, a LocalRepository is considered the
        install location)...it checks if the package is in the pth file
        (active/True) or not (deactivated/False)
        """
        #
        # if a pth file DNE, the package is assumed to be inactive
        #
        if( path.exists( self._pth_file ) ) :
            if( self._pth_lowercase_entries ) :
                package_fullname = package_fullname.lower()

            for line in self._get_pth_file_lines() :
                if( package_fullname == line ) :
                    return True

        return False


    def read_meta_data( self, url ) :
        """
        Returns the meta-data from the server associated with this repository
        (or the local file system) by fetching and reading the file then
        formatting it into a dictionary.
        """
        #
        # if no url, return no meta-data
        #
        if( not( url ) ) :
            return ""
        #
        # form the complete url if an absolute one was passed in based on the
        # url of the repository
        #
        if( not( url.startswith( self.location ) ) ) :
            if( self.location.endswith( "/" ) ) :
                complete_url = "%s%s" % (self.location, url)
            else :
                complete_url = "%s/%s" % (self.location, url)
        else :
            complete_url = url
        #
        # read in the meta-data string from the local file
        #
        fh = open( complete_url, "r" )
        md = fh.read()
        fh.close()

        return md


    def toggle_packages_active_state( self, package_fullnames ) :
        """
        This is used only in a LocalRepository, since all others dont
        have pth files (in this case, a LocalRepository is considered the
        install location)...it either adds or removes the package_fullnames to
        the LocalRepositorys pth file, thus deactivating or reactivating it.
        """
        #
        # an individual package or list of packages can be passed in, so
        # always make sure a list is used
        #
        if( type( package_fullnames ) != ListType ) :
            package_fullnames = [package_fullnames]
            
        #
        # if a pth file DNE, the package is assumed to be inactive, so
        # activate it by creating a pth file and adding the package to it
        #
        if( not( path.exists( self._pth_file ) ) ) :

            fh = self._open_pth_file_for_write( self._pth_file )
            if( fh is None ) :
                return
            
            lines = [self._pth_header] + package_fullnames + [self._pth_footer]
            for line in lines :
                fh.write( "%s\n" % line )
            fh.close()
        #
        # otherwise, either add or remove the package_fullnames to the pth file
        #
        else :
            if( self._pth_lowercase_entries ) :
                package_fullnames = [p.lower() for p in package_fullnames]
            #
            # compare against package name only when removing, so all matching
            # pacakges are removed, assuring that only one version is active
            #
            package_names = [p.split("-")[0] for p in package_fullnames]
            #
            # remove packages which are in the pth file that are to be
            # deactivated
            #
            new_lines = []
            for line in self._get_pth_file_lines() :
                #
                # compare the package name, but add/remove the fullname
                # (as stored in line)
                #
                package = line.split("-")[0]
                if( not( package in package_names ) ) :
                    new_lines.append( line )
                    
                elif( line in package_fullnames ) :
                    package_fullnames.remove( line )
            #
            # package_fullnames is now a list of packages which were not in the
            # pth file (packages needing to be reactivated), and new_lines is
            # the lines in the new pth file which must have the packages added
            #
            for package in package_fullnames :
                new_lines.insert( -1, package )

            #
            # finally, write out the new pth file if it is more than just the
            # header and footer
            #
            if( new_lines ) :
                if( (new_lines[0] == self._pth_header) and
                    (new_lines[1] == self._pth_footer) ) :
                    if( path.exists( self._pth_file ) ) :
                        self._remove_pth_file( self._pth_file )
                else :
                    fh = self._open_pth_file_for_write( self._pth_file )
                    if( fh is None ) :
                        return
                    
                    for line in new_lines :
                        fh.write( "%s\n" % line )
                    fh.close()


    #############################################################################
    # Protected interface.
    #############################################################################

    def _get_fixedup_url( self, url ) :
        """
        fix the url so it can easily refer to a local directory
        """
        fixed_url = url
        
        if( fixed_url != "" ) :
            fixed_url = path.normcase( path.normpath( fixed_url ) )

        if( fixed_url.lower().startswith( "file:" ) ) :
            fixed_url = fixed_url[5:]
        #
        # remove redundant leading slashes
        #
        if( fixed_url.startswith( os.sep ) ) :
            fixed_url = fixed_url.strip( os.sep )
            fixed_url = os.sep + fixed_url

        return fixed_url

        
    def _get_pth_file_lines( self ) :
        """
        Returns the contents of the pth file (with line endings fixed up) as
        a list of strings, or [] if pth file DNE

        FIXME: This has the potential to get called a lot...
        maybe cache it somehow?
        """
        pth_lines = []

        if( path.exists( self._pth_file ) ) :

            fh = open( self._pth_file, "ru" )
            lines = fh.readlines()
            fh.close()

            for line in lines :
                line = line.strip( "\n" )
                line = line.strip( "\r" )
                line = line.strip( "\r" )
                #
                # FIXME: quick fix since some Enthought eggs add "./" to the
                # front of the package name in the .pth file which dont match
                # any given package name.
                #
                if( line.startswith( "./" ) or line.startswith( ".\\" ) ) :
                    line = line[2:]
                    
                pth_lines.append( line )

        return pth_lines
    

    def _location_changed( self, old, new ) :
        """
        If the location changes, the path to the pth file needs updating.
        """
        self._pth_file = path.join( new, self._pth_filename )


    def _open_pth_file_for_write( self, pth_file ) :
        """
        Attempts to open a .pth file for writing and returns a file handle if
        successful.  If not, logs a message that the packages in that repo will
        not be able to have their active state changed and returns None.
        """
        fh = None
        try :
            fh = open( pth_file, "wu" )

        except IOError, err :
            msg = "Error: Could not modify %s (%s)..." % (pth_file, err) + \
                  "the active state of packages at this location will not " + \
                  "be changed.\n"
            self.log( msg )

        return fh


    def _remove_pth_file( self, pth_file ) :
        """
        Attempts to remove a .pth file and returns True if successful.  If not,
        logs a message that the packages in that repo will not be able to have
        their active state changed and returns False.
        """
        retcode = False
        try :
            os.remove( pth_file )
            retcode = True
            
        except OSError, err :
            msg = "Error: Could not modify %s (%s)..." % (pth_file, err) + \
                  "the active state of packages at this location will not " + \
                  "be changed.\n"
            self.log( msg )
            
        return retcode
    
