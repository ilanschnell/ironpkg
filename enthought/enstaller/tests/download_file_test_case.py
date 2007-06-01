#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007-02-09
#------------------------------------------------------------------------------

import sys
import os
from os import path
import unittest

from enstaller.run_enstaller import Downloader


class DownloadFileTestCase( unittest.TestCase ) :
    """
    TestCase which tests the methods used for downloading files in the bootstrap
    code (BaseEnstallerUtils).
    """
    #
    # a file which can be downloaded for testing
    #
    download_test_file = "download_test.txt"
    #
    # default to this URL for testing remote downloads
    #
    remote_url = "http://www.enthought.com/~rlratzel/enstaller_test/" + \
                 download_test_file
    #
    # the target dir - keep it in the same directory as the test suite
    #
    download_dir = path.abspath(path.dirname(__file__))
    #
    # the name of the file after its been downloaded
    #
    downloaded_file = path.join( download_dir, download_test_file )
    
    
    def __init__( self, *args ) :
        """
        Assume that the download dir exists and is writable.
        """
        super( DownloadFileTestCase, self ).__init__( *args )

        self.downloader = Downloader()

        
    def setUp( self ) :
        """
        This is called before each test.

        Since part of the test is checking that the visual output (download bar,
        progress %, etc.) is correct a new line should be printed between tests
        so the test runners output does not interfere.
        """
        print
        
    def tearDown(self):
        """
        Let's be safe and remove download file after each test
        """
        self._rm_f( self.downloaded_file )
        
    def test_file_does_not_exist( self ) :
        """
        This test checks that a file does not exist and needs to be downloaded.
        """

        self._rm_f( self.downloaded_file )
        
        self.failUnless(
            self.downloader.file_downloaded( self.remote_url,
                                             self.download_dir ) == False )

    def test_remote_download( self ) :
        """
        This test just checks that no exceptions are raised.
        """
        
        self._rm_f( self.downloaded_file )
        self.downloader.download_file( self.remote_url, self.download_dir )

        self.failUnless( path.exists( self.downloaded_file ) )
    

    def test_file_exists( self ) :
        """
        This test checks that a file which has already been downloaded matches
        the remote one.

        Seems kind of pointless to download a file then immmadiately check if
        the file was downloaded, but this keeps the tests independent, and
        accomplishes the same thing.
        """
        self._rm_f( self.downloaded_file )
        self.downloader.download_file( self.remote_url, self.download_dir )
        
        
        self.failUnless(
            self.downloader.file_downloaded( self.remote_url,
                                             self.download_dir ) == True )


    def test_file_exists_but_not_equal( self ) :
        """
        This test checks that a file exists but is not the same as the remote
        site (corrupted/partial download) and needs to be downloaded.
        """
        self._rm_f( self.downloaded_file )

        fh = open( self.downloaded_file, "w" )
        fh.write( "garbage\n" )
        fh.close()

        self.failUnless(
            self.downloader.file_downloaded( self.remote_url,
                                             self.download_dir ) == False )

        if( path.exists( DownloadFileTestCase.download_test_file ) ) :
            os.remove( DownloadFileTestCase.download_test_file )

    
    def test_local_download( self ) :
        """
        This tests that a file can be "downloaded" from a local repository.
        """
        local_file_name = path.basename( sys.executable )
        downloaded_file = path.join( self.download_dir, local_file_name )
        
        self._rm_f( downloaded_file )

        self.downloader.download_file( sys.executable, self.download_dir )
        #
        # do a more thorough check by comparing the "downloaded" file
        # contents to the original.
        #
        fh = open( sys.executable, "rb" )
        src_contents = fh.read()
        fh.close()
        fh = open( downloaded_file, "rb" )
        dest_contents = fh.read()
        fh.close()

        self.failUnlessEqual( src_contents, dest_contents,
                              msg="local download (copy) did not copy " + \
                              "contents correctly (files are not equal)" )

        if(path.exists(path.join(self.download_dir, path.basename(sys.executable)))) :
            os.remove(path.join(self.download_dir, path.basename(sys.executable)))


    def _rm_f( self, filename ) :
        """
        rm -f the file
        """
        if( path.exists( filename  ) ) :
            os.remove( filename )



if( __name__ == "__main__" ) :
    #
    # This loader will guarantee that the tests are run in a certain order.
    #
    class CustomLoader( unittest.TestLoader ) :
        def getTestCaseNames( self, *args ) :
            return [
                "test_file_does_not_exist",
                "test_remote_download",
                "test_file_exists",
                "test_file_exists_but_not_equal",
                "test_local_download",
                ]

    unittest.main( testLoader=CustomLoader() )

