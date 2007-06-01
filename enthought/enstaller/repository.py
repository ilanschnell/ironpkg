#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2006-06-22
#------------------------------------------------------------------------------

import sys
import distutils.sysconfig

from pkg_resources import \
     parse_requirements, Distribution

from enthought.traits.api import \
     HasTraits, List, Str

from enthought.enstaller.text_io import \
     TextIO
from enthought.enstaller.enstaller_traits import \
     ExistingDir
from enthought.enstaller.package import \
     Package, is_egg_installable



class Repository( HasTraits, TextIO ) :
    """
    Base class used for maintaining a collection of package objects.

    Derivations of this class include remote and local repositories.

    If remote, the repository is a single URL, and if local the repository is a
    single directory.  Multiple repositories (say, a PYTHONPATH) are handled
    elsewhere, probably as a list of Repository instances
    """
    #
    # Assume a local repo and force the location to be an existing directory.
    #
    location = ExistingDir( abspath=True )

    #
    # The list of package objects in the repo.
    #
    packages = List( Package )

    #
    # for later...these need to be more secure, possibly
    #
    login = Str
    password = Str


    def __init__( self, **kwargs ) :
        """
        Required to be called with non-Traits TextIO args and have them set
        properly.  Also sets TextIO attrs with defaults.
        """
        self.verbose = kwargs.pop( "verbose", False )
        self.prompting = kwargs.pop( "prompting", True )
        self.logging_handle = kwargs.pop( "logging_handle", sys.stdout )

        super( Repository, self ).__init__( **kwargs )


    def build_package_list( self ) :
        """
        extended in derived classes, then called afterwards if desired to
        remove packages that arent installable
        """
        #
        # go through each of the package objects and keep only those which are
        # installable on this platform
        #
        tmp = self.packages
        self.packages = []
        for p in tmp :

            if( is_egg_installable( p.fullname ) ) :
                self.packages.append( p )


    def find_packages( self, package_specs ) :
        """
        Returns a list of package objects in the repository with names that
        match any of the package_specs
        """
        if( len( package_specs ) == 0 ) :
            pkgs = self.packages

        else :
            pkgs = []
            #
            # use the setuptools Requirement (parse_requirements returns a list
            # of them) and Distribution objects to test if the package_specs
            # strings (which are just setuptools requirement strings) match the
            # packages
            #
            requirements = list( parse_requirements( "\n".join( package_specs)))

            for pkg in self.packages :
                dist = Distribution.from_filename( pkg.fullname )
                for req in requirements :
                    if( dist in req ) :
                        pkgs.append( pkg )

        return pkgs
            

    def get_active_packages( self ) :
        """
        This is implemented only in a LocalRepository, since all others dont
        have pth files (in this case, the LocalRepository is considered the
        install location)
        """
        raise NotImplementedError


    def toggle_packages_active_state( self, package_fullnames ) :
        """
        This is implemented only in a LocalRepository, since all others dont
        have pth files (in this case, the LocalRepository is considered the
        install location)
        """
        raise NotImplementedError
    


################################################################################
# Quick testing with "python -i <module>"
################################################################################

if( __name__ == "__main__" ) :
    import sys
    r = Repository( location=sys.argv[1] )
    r.build_package_list()
    
