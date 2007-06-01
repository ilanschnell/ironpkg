#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Deepu Sudhakar - 2007-03-23
#------------------------------------------------------------------------------

import unittest
import shutil
import os
import sys

from os import path

from enstaller.easy_installer import \
     EasyInstaller
     
from enthought.traits.api import \
     HasTraits, TraitError

# Convenient global variables specifying dir locations
CURRENT_DIR = path.abspath(path.dirname(__file__))
LOCAL_REPO = path.normcase(path.abspath(path.join(CURRENT_DIR, "test_repo")))
INSTALL_DIR = path.normcase(path.abspath(path.join(CURRENT_DIR, "install")))


# ----------------------------------------------------------------
# Test case for EasyInstaller and associated operations.
# ----------------------------------------------------------------
class EasyInstallerTestCase( unittest.TestCase ) :
    
    
    def __init__( self, *args ) :
        super( EasyInstallerTestCase, self ).__init__( *args )
        
    
    # -------------------------------------------
    # Set up an instance of an EnstallerEngine
    # -------------------------------------------          
    def setUp(self):
        os.mkdir(INSTALL_DIR)
        self.easy_installer = EasyInstaller()
        self.easy_installer.find_links = [LOCAL_REPO]
        self.easy_installer.verbose = False
    
    
    # -------------------------------------------
    # Remove the dummy install after each test
    # ------------------------------------------- 
    def tearDown(self):
        shutil.rmtree(INSTALL_DIR)
        
    
    # -------------------------------------------
    # Test installing a specified package
    # -------------------------------------------
    def test_install_specified(self):
        self.easy_installer.install(INSTALL_DIR, "foo==0.0.1.dev007")
        
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "foo-0.0.1.dev007-py2.4-win32.egg")))
        self.assertTrue(self._search_easy_install_pth("foo-0.0.1.dev007-py2.4-win32.egg"))
        
        
    # -------------------------------------------
    # Test installing the latest package
    # -------------------------------------------
    def test_install_latest(self):
        self.easy_installer.install(INSTALL_DIR, "foo")
        
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "foo-0.0.2.dev007-py2.4-win32.egg")))
        self.assertTrue(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
    
    
    # ------------------------------------------------------
    # Test installing an older package on top of a newer one
    # ------------------------------------------------------
    def test_install_conflict(self):
        self.easy_installer.install(INSTALL_DIR, "foo")
        
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "foo-0.0.2.dev007-py2.4-win32.egg")))
        self.assertTrue(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
        
        self.easy_installer.install(INSTALL_DIR, "foo==0.0.1.dev007")
        
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "foo-0.0.1.dev007-py2.4-win32.egg")))
        self.assertTrue(self._search_easy_install_pth("foo-0.0.1.dev007-py2.4-win32.egg"))


    # -----------------------------------------------------------
    # Helper function to look for an egg name in easy-install.pth
    # -----------------------------------------------------------
    def _search_easy_install_pth(self, package_name):
        try:
            f = open(path.join(INSTALL_DIR, "easy-install.pth"), 'r')
        
        except IOError:
            return False
        
        else:
            lines = f.readlines()
            del lines[0]
            del lines[-1]
            
            eggs = []
            for line in lines:
                if line.startswith("./"):
                    eggs.append(line[2:].strip())
                else:
                    eggs.append(line.strip())
                    
            return package_name in eggs

        
if( __name__ == "__main__" ) :
    unittest.main()
