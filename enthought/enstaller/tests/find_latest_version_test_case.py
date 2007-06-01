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

import sys
from os import path
import unittest

from enstaller.run_enstaller import Downloader


class FindLatestVersionTestCase( unittest.TestCase ) :
    """
    TestCase which tests the find_latest_version function used for finding the
    latest version of a particular file, based on file name.
    """

    def __init__( self, *args ) :
        """
        Create a RepoUtils instance for testing the find_latest_version
        function.
        """
        super( FindLatestVersionTestCase, self ).__init__( *args )

        self.downloader = Downloader()

        
    def setUp( self ) :
        """
        Clear the test vars before each test.
        """
        #
        # self.url is the location of an egg repo
        # self.file_patt is an re-style pattern which matches >=1 egg in the repo
        # self.latest_version is the expected "latest version" of the file in
        # the repo
        #
        self.url = "http://www.enthought.com/~rlratzel/enstaller_test/eggs_flat"

        self.file_patt = ""
        self.latest_version = ""
        

    def test_cheetah( self ) :
        self.file_patt = "Cheetah-(.*)-py2.4.egg$"
        self.latest_version = "Cheetah-2.0rc7-py2.4.egg"
        self.__lookup_and_compare()

    def test_f2py( self ) :
        self.file_patt = "F2PY-(.*)-py2.5.egg$"
        self.latest_version = "F2PY-2.45.241_1926-py2.5.egg"
        self.__lookup_and_compare()

    def test_enstaller( self ) :
        pyver = "%s.%s" % (sys.version_info[0], sys.version_info[1])
        self.file_patt = "enstaller-(0\.1\..*)-py%s.*\.egg$" % pyver
        self.latest_version = "enstaller-0.1.10-py%s-win32.egg" % pyver
        self.__lookup_and_compare()
    
    def test_enthought( self ) :
        self.file_patt = "enthought-(.*)-py.*.egg$"
        self.latest_version = "enthought-1.1.1_r10037-py2.4-win32.egg"
        self.__lookup_and_compare()

    def test_setuptools( self ) :
        self.file_patt = "setuptools-(.*)-py.*.egg$"
        self.latest_version = "setuptools-0.7a1dev_r53614-py2.4.egg"
        self.__lookup_and_compare()

    def test_swig( self ) :
        self.file_patt = "SWIG-(.*)-.*.egg$"
        self.latest_version = "SWIG-1.3.31-win32.egg"
        self.__lookup_and_compare()

    def test_testoob_latest( self ) :
        self.file_patt = "testoob-(.*)-py.*.egg$"
        self.latest_version = "testoob-latest-py2.4.egg"
        self.__lookup_and_compare()


    def __lookup_and_compare( self ) :
        observed = self.downloader.find_latest_version( self.url,
                                                        self.file_patt )
        expected = path.join( self.url, self.latest_version )
        # for Windoze
        expected = expected.replace( "\\", "/" )
        self.assertEqual( observed, expected )


if( __name__ == "__main__" ) :
    unittest.main()
