#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007-02-19
#------------------------------------------------------------------------------

import os
import unittest
import shutil
from os import path

try :
    from testoob import testing
except ImportError :
    class testoob :
        def skip( self, msg ) :
            return
        
from enstaller.enstaller_traits import \
     Url, ExistingDir, CreatableDir, ExistingFile
     
from enstaller.run_enstaller import \
     IS_WINDOWS

from enthought.traits.api import \
     HasTraits, TraitError


class DatatypeTestCase( unittest.TestCase ) :
    """
    TestCase which tests the various custom datatypes used in Esntaller.
    """

    def __init__( self, *args ) :
        """
        Create some classes with the datatypes for testing.
        """
        super( DatatypeTestCase, self ).__init__( *args )

        class ExistingFileTester( HasTraits ) :
            f = ExistingFile
        
        class ExistingFileAbspathTester( HasTraits ) :
            f = ExistingFile( abspath=True )
            
        class UrlTester( HasTraits ) :
            url = Url

        class ExistingDirTester( HasTraits ) :
            d = ExistingDir

        class ExistingDirWritableTester( HasTraits ) :
            d = ExistingDir( writable=True )

        class ExistingDirAbspathTester( HasTraits ) :
            d = ExistingDir( abspath=True )

        class ExistingDirWritableAbspathTester( HasTraits ) :
            d = ExistingDir( writable=True, abspath=True )

        class CreatableDirTester( HasTraits ) :
            d = CreatableDir

        class CreatableDirAbspathTester( HasTraits ) :
            d = CreatableDir( abspath=True )

        class CreatableDirCreateTester( HasTraits ) :
            d = CreatableDir( create=True )

        class CreatableDirAbspathCreateTester( HasTraits ) :
            d = CreatableDir( abspath=True, create=True )

            
        self.url_tester = UrlTester()
        
        self.existingfile_tester = ExistingFileTester()
        self.existingfile_abspath_tester = ExistingFileAbspathTester()

        self.existingdir_tester = ExistingDirTester()
        self.existingdir_writable_tester = ExistingDirWritableTester()
        self.existingdir_abspath_tester = ExistingDirAbspathTester()
        self.existingdir_writable_abspath_tester = \
                                         ExistingDirWritableAbspathTester()

        self.createabledir_tester = CreatableDirTester()
        self.createabledir_abspath_tester = CreatableDirAbspathTester()
        self.createabledir_create_tester = CreatableDirCreateTester()
        self.createabledir_abspath_create_tester = \
                                         CreatableDirAbspathCreateTester()
        

    def setUp( self ) :
        """
        This is called before each test.
        """
        if( not( path.exists( "./for_testing" ) ) ) :
            os.mkdir( "./for_testing", 0555 )


    def tearDown( self ) :
        """
        This is called after every test.
        """
        if( path.exists( "./foo" ) and path.isdir( "./foo" ) ) :
            shutil.rmtree( "./foo" )
            
   
    def test_existing_file(self):
        f = path.abspath(__file__)
        self.existingfile_tester.f = f
        self.assertEqual(self.existingfile_tester.f, f)
    
    
    def test_existing_file_relpath(self):
        f = __file__
        self.existingfile_tester.f = f
        self.assertEqual(self.existingfile_tester.f, f)
        
    
    def test_existing_file_abspath(self):
        f = __file__
        self.existingfile_abspath_tester.f = f
        self.assertEqual(self.existingfile_abspath_tester.f, path.normcase(path.abspath(__file__)))
    
    
    def test_existing_file_not_existing(self):
        f = "./foobarbaz.txt"
        def apply() :
            self.existingfile_tester.f = f
        self.failUnlessRaises(TraitError, apply)
            
    
    def test_valid_remote_url_http( self ) :
        u = "http://foo.bar/baz"
        self.url_tester.url = u
        self.assertEqual( self.url_tester.url, u )


    def test_valid_remote_url_https( self ) :
        u = "https://foo.bar/baz"
        self.url_tester.url = u
        self.assertEqual( self.url_tester.url, u )


    def test_valid_remote_url_ftp( self ) :
        u = "ftp://foo.bar/baz"
        self.url_tester.url = u
        self.assertEqual( self.url_tester.url, u )

        
    def test_valid_local_url_dirname( self ) :
        u = os.getcwd()
        self.url_tester.url = u
        self.assertEqual( self.url_tester.url, "file://%s" % u )
        

    def test_valid_local_url_file_colon( self ) :
        u = "file://%s" % os.getcwd()
        self.url_tester.url = u
        self.assertEqual( self.url_tester.url, "file://%s" % os.getcwd() )


    def test_invalid_remote_url( self ) :
        u = "foo://foo.bar"
        def apply() :
            self.url_tester.url = u
        self.failUnlessRaises( TraitError, apply )


    def test_invalid_local_url( self ) :
        u = "foobar"
        def apply() :
            self.url_tester.url = u
        self.failUnlessRaises( TraitError, apply )


    def test_invalid_local_url_file_colon( self ) :
        u = "file:///foobar"
        def apply() :
            self.url_tester.url = u
        self.failUnlessRaises( TraitError, apply )


    def test_existing_dir( self ) :
        d = os.getcwd()
        self.existingdir_tester.d = d
        self.assertEqual( self.existingdir_tester.d, d )


    def test_existing_dir_relpath( self ) :
        d = "."
        self.existingdir_tester.d = d
        self.assertEqual( self.existingdir_tester.d, d )


    def test_existing_dir_abspath( self ) :
        d = "."
        self.existingdir_abspath_tester.d = d
        self.assertEqual( self.existingdir_abspath_tester.d, path.normcase(os.getcwd()) )


    def test_existing_dir_writable( self ) :
        d = "."
        self.existingdir_writable_tester.d = d
        self.assertEqual( self.existingdir_writable_tester.d, d )


    def test_existing_dir_writable_abspath( self ) :
        d = "."
        self.existingdir_writable_abspath_tester.d = d
        self.assertEqual( self.existingdir_writable_abspath_tester.d,
                          path.normcase(os.getcwd()) )


    def test_createable_dir( self ) :
        d = "./foo"
        self.createabledir_tester.d = d
        self.assertEqual( self.createabledir_tester.d, d )


    def test_createable_abspath_dir( self ) :
        d = "./foo"
        self.createabledir_abspath_tester.d = d
        self.assertEqual( self.createabledir_abspath_tester.d,
                          path.join( path.normcase(os.getcwd()), "foo" ) )


    def test_createable_create_dir( self ) :
        d = "./foo"
        self.createabledir_create_tester.d = d
        self.assertEqual( self.createabledir_create_tester.d, d )
        self.assertEqual( True, (path.exists( d ) and path.isdir( d )) )


    def test_createable_abspath_create_dir( self ) :
        d = "./foo/bar/baz"
        self.createabledir_abspath_create_tester.d = d
        self.assertEqual( self.createabledir_abspath_create_tester.d,
                          path.join( path.normcase(os.getcwd()), "foo", "bar", "baz" ) )
        self.assertEqual( True, (path.exists( d ) and path.isdir( d )) )

    """
    The following tests do not work on Windows since
    it uses ACLs to control file permissions instead file modes.
    We skip them if we detect we're on Windows (for Marathon).
    """
            
    def test_existing_dir_not_writable( self ) :
        if IS_WINDOWS:
            testing.skip("Skipping test since file permissions are not testable on Windows.")
        
        d = path.join( os.getcwd(), "for_testing" )
        def apply() :
            self.existingdir_writable_tester.d = d
        self.failUnlessRaises( TraitError, apply )


    def test_existing_dir_not_writable_root( self ) :
        if IS_WINDOWS:
            testing.skip("Skipping test since file permissions are not testable on Windows.")
            
        d = "/"
        def apply() :
            self.existingdir_writable_tester.d = d
        self.failUnlessRaises( TraitError, apply )


    def test_existing_dir_not_writable_abspath( self ) :
        if IS_WINDOWS:
            testing.skip("Skipping test since file permissions are not testable on Windows.")
            
        d = "/"
        def apply() :
            self.existingdir_writable_abspath_tester.d = d
        self.failUnlessRaises( TraitError, apply )


    def test_createable_not_createable( self ) :
        if IS_WINDOWS:
            testing.skip("Skipping test since file permissions are not testable on Windows.")
            
        d = "/usr/bin/foo/bar"
        def apply() :
            self.createabledir_tester.d = d
        self.failUnlessRaises( TraitError, apply )


    def test_createable_exists_not_writable( self ) :
        if IS_WINDOWS:
            testing.skip("Skipping test since file permissions are not testable on Windows.")
            
        d = "./for_testing"
        def apply() :
            self.createabledir_tester.d = d
        self.failUnlessRaises( TraitError, apply )


    def test_createable_create_exists_not_writable( self ) :
        if IS_WINDOWS:
            testing.skip("Skipping test since file permissions are not testable on Windows.")
            
        d = "./for_testing/foo/bar"
        def apply() :
            self.createabledir_tester.d = d
        self.failUnlessRaises( TraitError, apply )


if( __name__ == "__main__" ) :
    unittest.main()
    
