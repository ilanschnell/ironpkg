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
     Property, Instance

from enthought.enstaller.url_util import \
     URLUtil
from enthought.enstaller.enstaller_traits import \
     Url
from enthought.enstaller.repository import \
     Repository
from enthought.enstaller.package import \
     Package
from enthought.enstaller.html_parsing import \
     EggHTMLFormatter, EggHTMLPyPIParser
from enthought.enstaller.pypi_xmlrpc import \
     PypiXMLRPCEggFinder



class PypiRepository( Repository ) :
    """
    A PyPI-style repository.

    PyPI repositories support XMLRPC, *or* have a specific heirarchy of HTML
    pages used for organizing their packages.
    """
    #
    # The location is a property for a PyPI repo, since URLs which refer to
    # the cheeseshop need to be "fixed up" occasionally.
    #
    location = Property
    _location = Url
    
    #
    # the XMLRPC server instance, if the repo supports it
    #
    xmlrpc_server = None

    #
    # Instance of a URLUtil used for accessing URLs with error handling.
    #
    _urlutil = Instance( URLUtil )


    def build_package_list( self ) :
        """
        Builds a list of packages from a pypi-style site by first attempting to
        use an XMLRPC connection, and if thats not available, revert to
        traversing the dir hierarchy (meta-data will be fetched with XMLRPC
        calls if somehow available later)
        """
        #
        # UPDATE: since the XMLRPC interface forces a check for eggs on
        # packages which dont even release any files, it is much slower than
        # checking the HTML pages since they only contain packages which
        # release files...also, the XMLRPC calls dont seem to return as many
        # egg pacakges (maybe thats more accurate?)
        #
        if False :
        #if( not( self.xmlrpc_server is None ) ) :
            self.packages = self._build_package_list_from_pypi_xmlrpc()
            
        else :
            self.packages = self._build_package_list_from_pypi_html()

        Repository.build_package_list( self )
                

    def query_meta_data( self, package_name, package_version ) :
        """
        Returns the meta-data for the package+version from a pypi-style
        XMLRPC call.
        """
        md = {}
        if( not( self.xmlrpc_server is None ) ) :
            try :
                md = self.xmlrpc_server.release_data( package_name,
                                                      package_version )
            except Exception, err :
                self.log( "Problem reading meta-data for %s-%s...skipping.\n" % \
                          (package_name, package_version) )
                self.debug( "(problem was: %s)\n" % err )
                
        else :
            print \
                  "Cannot fetch meta-data from pypi-style site because " + \
                  "%s does not support XMLRPC calls" % self.location

        return md


    #############################################################################
    # Protected interface.
    #############################################################################

    def _build_package_list_from_pypi_html( self ) :
        """
        Uses the PyPI html parser to traverse a PyPI site''s html pages (using
        multiple threads) to harvest package information.
        """
        egg_formatter = EggHTMLFormatter()
        egg_html_parser = EggHTMLPyPIParser( self.location,
                                             egg_formatter,
                                             logging_handle=self.logging_handle,
                                             verbose=self.verbose,
                                             prompting=self.prompting )

        packages = []
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
                    if( egg_info.has_key( "info_url" ) ) :
                        p = Package( repository=self )
                        p.info_url = egg_info["info_url"]
                        p.fullname = path.basename( egg_info["download_url"] )
                        p.location = path.dirname( egg_info["download_url"] )
                    else :
                        p = Package( repository=self,
                                     egg_url=egg_info["download_url"] )

                    packages.append( p )

            egg_html_parser.close()

        return packages


    def _build_package_list_from_pypi_xmlrpc( self ) :
        """
        Uses an XMLRPC connection to build a list of Package objects from a
        PyPI-based site which supports it.
        """
        egg_finder = PypiXMLRPCEggFinder( self.xmlrpc_server )
        urls = egg_finder.find_egg_packages()
        packages = []

        for url in urls :
            packages.append( Package( repository=self, egg_url=url ) )

        return packages


    #############################################################################
    # Traits handlers, defaults, etc.
    #############################################################################

    def _get_location( self ) :
        """
        Getter for location.
        """
        return self._location


    def _set_location( self, url ) :
        """
        Setter for location.
        
        IMPORTANT: the python.org pypi sites will be renamed to
        http://cheeseshop.python.org internally, eventhough
        http://python.org/pypi is the same thing.  This is so that /packages can
        be appended to the end and a dir-listing-style output can be processed.
        All other non-python.org sites are expected to support an addition of
        /packages
        """
        fixed_url = url

        if( "python.org" in fixed_url ) :
            fixed_url = "http://cheeseshop.python.org"

        if( not( fixed_url.endswith( "/packages" ) ) ) :

            if( fixed_url.endswith( "/" ) ) :
                fixed_url = fixed_url[:-1]

            fixed_url += "/packages"

        self._location = fixed_url
        

    def __urlutil_default( self ) :
        """
        Return a default instance of a URLUtil to use.
        """

        return URLUtil( logging_handle=self.logging_handle,
                        verbose=self.verbose,
                        prompting=self.prompting )

