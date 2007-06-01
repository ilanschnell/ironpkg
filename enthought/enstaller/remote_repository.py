#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2006-08-10
#------------------------------------------------------------------------------

import os
from os import path

from enthought.traits.api import \
     Instance

from enstaller.run_enstaller import \
     URLUtil
from enstaller.enstaller_traits import \
     Url
from enstaller.repository import \
     Repository
from enstaller.package import \
     Package
from enstaller.html_parsing import \
     EggHTMLFormatter, EggHTMLDirListingParser



class RemoteRepository( Repository ) :
    """
    A remote repository (but not a PyPI-style repository).
    """

    #
    # The location for a remote repo is always a URL
    #
    location = Url

    #
    # Instance of a URLUtil used for accessing URLs with error handling.
    #
    _urlutil = Instance( URLUtil )

        
    def build_package_list( self ) :
        """
        Returns a list of packages retrieved from the remote source by using
        the html parser passed in.
        """
        egg_formatter = EggHTMLFormatter()
        egg_html_parser = EggHTMLDirListingParser(
            self.location,
            egg_formatter,
            only_find_installable=True,
            logging_handle=self.logging_handle,
            verbose=self.verbose,
            prompting=self.prompting )

        self.packages = []

        url_handle = self._urlutil.urlopen( self.location )

        #
        # Continue only if the URL could be accessed.
        #
        if( not( url_handle is None ) ) :

            http_response = url_handle.read()
            egg_html_parser.feed( http_response )

            for (egg_name, egg_info) in egg_html_parser.get_egg_info() :
                #
                # dont add unless a download_url is present (no download_url
                # means only a .info file was found, but no egg)
                #
                if( egg_info.has_key( "download_url" ) ) :
                    p = Package( repository=self,
                                 egg_url=egg_info["download_url"] )

                    if( egg_info.has_key( "info_url" ) ) :
                        p.info_url = egg_info["info_url"]

                    self.packages.append( p )

            egg_html_parser.close()

            Repository.build_package_list( self )


    def read_meta_data( self, url ) :
        """
        Returns the meta-data from the server associated with this repository
        by fetching and reading the file.
        """
        meta_data = ""
        #
        # if no url, return no meta-data
        #
        if( not( url ) ) :
            return meta_data
        #
        # form the complete url if an absolute one was passed in based on the
        # url of the repository
        #
        if( not( url.startswith( self.location ) ) ) :
            if( self.locaiton.endswith( "/" ) ) :
                complete_url = "%s%s" % (self.locaiton, url)
            else :
                complete_url = "%s/%s" % (self.locaiton, url)
        else :
            complete_url = url

        #
        # read in the meta-data string by fetching the url
        # from a server and reading it, if possible.
        #
        url_handle = self._urlutil.urlopen( complete_url )

        if( not( url_handle is None ) ) :
            meta_data = url_handle.read()

        return meta_data


    #############################################################################
    # Traits handlers, defaults, etc.
    #############################################################################

    def __urlutil_default( self ) :
        """
        Return a defualt instance of a URLUtil to use.
        """

        return URLUtil( logging_handle=self.logging_handle,
                        verbose=self.verbose,
                        prompting=self.prompting )



################################################################################
# Quick testing with "python -i <module>"
################################################################################

if( __name__ == "__main__" ) :
    import sys
    r = RemoteRepository( url=sys.argv[1] )
    r.build_package_list()
    
