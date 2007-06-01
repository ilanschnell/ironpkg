#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007-02-07
#------------------------------------------------------------------------------

import unittest

from enstaller.run_enstaller import Downloader


class VersionCmpTestCase( unittest.TestCase ) :
    """
    TestCase which tests the version_cmp function used in determining if
    a version string is higher or lower than another one.

    self.versions is a list of version strings which are to be sorted in
    increasing order.

    self.ordered_versions is the list of version strings properly sorted in
    increasing order, used for verification.
    """

    def __init__( self, *args ) :
        """
        Create a RepoUtils instance for testing the version_cmp function.
        """
        super( VersionCmpTestCase, self ).__init__( *args )

        self.downloader = Downloader()
        

    def setUp( self ) :
        """
        Clear the lists before each test.
        """
        self.versions = []
        self.ordered_versions = []


    def test_simple( self ) :
        self.versions = ["0.0.2", "0.0.1"]
        self.ordered_versions = ["0.0.1", "0.0.2"]
        self.__sort_and_compare()
        
    def test_letters( self ) :
        self.versions = ["1.0.0", "1.0.0a"]
        self.ordered_versions = ["1.0.0a", "1.0.0"]
        self.__sort_and_compare()
        
    def test_dashes( self ) :
        self.versions = ["0.0.2-dev", "0.0.1", "0.0.1-foo"]
        self.ordered_versions = ["0.0.1", "0.0.1-foo", "0.0.2-dev"]
        self.__sort_and_compare()
        
    def test_length( self ) :
        self.versions = ["1.2.0", "1.2"]
        self.ordered_versions = ["1.2", "1.2.0"]
        self.__sort_and_compare()

    def test_big( self ) :
        self.versions = \
            ["4.0-dev", "4.1", "0.0.1", "1.0.0", "1.0.0a", "1.0.1",
             "1.1.0a", "1.1.1", "1.1.1a", "0.2.1-dev", "1.0",]
        self.ordered_versions = \
            ["0.0.1", "0.2.1-dev", "1.0", "1.0.0a", "1.0.0", "1.0.1",
             "1.1.0a", "1.1.1a", "1.1.1", "4.0-dev", "4.1",]
        self.__sort_and_compare()
        

    def __sort_and_compare( self ) :
        self.versions.sort( cmp=self.downloader.version_cmp )
        self.assertEqual( self.versions, self.ordered_versions )



if( __name__ == "__main__" ) :
    unittest.main()
