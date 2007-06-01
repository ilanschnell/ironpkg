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

#
# This module provides classes which scan a PyPI XMLRPC connection for various
# packages.  The classes utilize therads to search for packages in parallel.
#

from threading import \
     Thread


class PypiXMLRPCPackageChecker( Thread ) :
    """
    Checks to see if a specific type of package type (egg, rpm, etc.) exists
    for a given package by querying a PyPI XMLRPC connection.  This class is
    derived from Thread so it can be spawned in a spearate thread.
    """

    def __init__( self, server, package_name, package_type ) :
        """
        construct with a server to PyPI query, the name of the package to look
        for, and the package type required.
        """
        Thread.__init__( self )
        self.server = server
        self.package_name = package_name
        self.package_type = package_type
        self.urls = []
        

    def get_urls( self ) :
        """
        Return the search results
        """
        return self.urls


    def run( self ) :
        """
        Run the check.  Look for the package type for the specified package
        """
        got_somthing = 0

        for ver in self.server.package_releases( self.package_name ) :

            for url in self.server.release_urls( self.package_name, ver ) :

                if( url["packagetype"] == self.package_type ):
                    print "Found (via XMLRPC): ", url["url"]
                    got_somthing += 1
                    self.urls.append( url["url"] )

        if( got_somthing == 0 ) :
            print "no packages of type %s found for: %s" % (self.package_type,
                                                            self.package_name)

    

class PypiXMLRPCEggFinder :
    """
    Spawns max_threads number of threads in order to find packages which have
    egg files on the server.
    """
    
    def __init__( self, server, max_threads=30 ) :
        """
        construct with a server and the max number of threads to spawn
        """
        self.package_type = "bdist_egg"
        self.server = server
        self.egg_urls = []
        self.threads_running = 0
        self.max_threads = max_threads
        self.checkers = []

        
    def find_egg_packages( self ) :
        """
        spawns the individual threads which run a PypiXMLRPCPackageChecker set
        to search for bdist_egg and gathers and returns the results.
        """
        self.egg_urls = []
        self.checkers = []
        self.threads_running = 0
        #
        # spawn a thread for each package available, synchronize one
        # max_threads have been spawned.
        #
        for package in self.server.list_packages() :
            checker = PypiXMLRPCPackageChecker( self.server, package,
                                                self.package_type )

            self.checkers.append( checker )
            checker.start()
            self.threads_running += 1

            if( self.threads_running >= self.max_threads ) :
                self.sync()
        #
        # do a final sync and return the results
        #
        self.sync()
        return self.egg_urls
    

    def sync( self ) :
        """
        Iterates over all the outstanding threads and calls join() on them,
        which causes them to "join" with the main thread (I think).  After that,
        their results can be combined and the thread count and list can be
        reset.
        """
        for checker in self.checkers :
            checker.join()
            self.egg_urls += checker.get_urls()

        self.checkers = []
        self.threads_running = 0
