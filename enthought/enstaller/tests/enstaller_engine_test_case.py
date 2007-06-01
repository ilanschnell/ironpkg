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

from enstaller.enstaller_engine import \
     EnstallerEngine
     
from enstaller.package import \
     Package
     
from enthought.traits.api import \
     HasTraits, TraitError

# Convenient global variables specifying dir locations
CURRENT_DIR = path.abspath(path.dirname(__file__))
LOCAL_REPO = path.normcase(path.abspath(path.join(CURRENT_DIR, "test_repo")))
INSTALL_DIR = path.normcase(path.abspath(path.join(CURRENT_DIR, "install")))


# ----------------------------------------------------------------
# Test case for EnstallerEngine and associated operations.
# ----------------------------------------------------------------
class EnstallerEngineTestCase( unittest.TestCase ) :
    
    
    def __init__( self, *args ) :
        super( EnstallerEngineTestCase, self ).__init__( *args )
        
    
    # -------------------------------------------
    # Set up an instance of an EnstallerEngine
    # -------------------------------------------          
    def setUp(self):      
        self.engine = EnstallerEngine()
        self.engine.find_links = [LOCAL_REPO]
    
    
    # -------------------------------------------
    # Remove the dummy install after each test
    # ------------------------------------------- 
    def tearDown(self):
        shutil.rmtree(INSTALL_DIR)
        
    
    # -------------------------------------------
    # Test installing a package
    # -------------------------------------------
    def test_install(self):
        self.engine.install(INSTALL_DIR, ["foo", "bar", "baz"])
        
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "foo-0.0.2.dev007-py2.4-win32.egg")))
        self.assertTrue(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
        
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "bar-2.0.0-py2.4-win32.egg")))
        self.assertTrue(self._search_easy_install_pth("bar-2.0.0-py2.4-win32.egg"))
        
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "baz-0.0.7-py2.4-win32.egg")))
        self.assertTrue(self._search_easy_install_pth("baz-0.0.7-py2.4-win32.egg"))
        
    
    # -------------------------------------------
    # Test removing a package
    # -------------------------------------------        
    def test_remove(self):
        foo_pkg = Package(name = "foo",
                          version = "0.0.2.dev007",
                          raw_version = "0.0.2.dev007",
                          location = INSTALL_DIR,
                          fullname = "foo-0.0.2.dev007-py2.4-win32.egg")
        
        bar_pkg = Package(name = "bar",
                          version = "2.0.0",
                          raw_version = "2.0.0",
                          location = INSTALL_DIR,
                          fullname = "bar-2.0.0-py2.4-win32.egg")
        
        
        self.engine.install(INSTALL_DIR, ["foo", "bar"])
        
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "foo-0.0.2.dev007-py2.4-win32.egg")))
        self.assertTrue(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
        
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "bar-2.0.0-py2.4-win32.egg")))
        self.assertTrue(self._search_easy_install_pth("bar-2.0.0-py2.4-win32.egg"))
        
        self.engine.remove([foo_pkg, bar_pkg])
        
        self.assertFalse(path.exists(path.join(INSTALL_DIR, "foo-0.0.2.dev007-py2.4-win32.egg")))
        self.assertFalse(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
        
        self.assertFalse(path.exists(path.join(INSTALL_DIR, "bar-2.0.0-py2.4-win32.egg")))
        self.assertFalse(self._search_easy_install_pth("bar-2.0.0-py2.4-win32.egg"))


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
