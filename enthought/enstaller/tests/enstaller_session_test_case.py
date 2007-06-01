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

from enstaller.enstaller_session import \
     EnstallerSession
     
from enthought.traits.api import \
     HasTraits, TraitError

# Convenient global variables specifying dir locations
CURRENT_DIR = path.abspath(path.dirname(__file__))
LOCAL_REPO = path.normcase(path.abspath(path.join(CURRENT_DIR, "test_repo")))
INSTALL_DIR = path.normcase(path.abspath(path.join(CURRENT_DIR, "install")))


# ----------------------------------------------------------------
# Test case for EnstallerSession and associated operations.
# ----------------------------------------------------------------
class EnstallerSessionTestCase( unittest.TestCase ) :
    
    
    def __init__( self, *args ) :
        super( EnstallerSessionTestCase, self ).__init__( *args )
        
    
    # -------------------------------------------
    # Set up a session
    # -------------------------------------------          
    def setUp(self):
        self.session = EnstallerSession(find_links = [LOCAL_REPO],
                                        install_dir = INSTALL_DIR,
                                        verbose = False,
                                        prompting = False)
        self.session.initialize()
        self.session.read_repositories() 
    
    
    # -------------------------------------------
    # Remove the dummy install after each test
    # ------------------------------------------- 
    def tearDown(self):
        shutil.rmtree(INSTALL_DIR)
        
    
    # -------------------------------------------
    # Test installing a package
    # -------------------------------------------
    def test_install(self):
        self.session.install(["foo"])
        
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "foo-0.0.2.dev007-py2.4-win32.egg")))
        self.assertTrue(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
        
    
    # -------------------------------------------
    # Test removing a package
    # -------------------------------------------    
    def test_remove(self):
        self.session.install(["foo"])
        inst_p = self.session.get_installed_packages()
        package_to_remove = self._search_pkg_obj_list("foo", "0.0.2.dev007", inst_p)
        
        self.session.remove(package_to_remove)
        
        self.assertFalse(path.exists(path.join(INSTALL_DIR, "foo-0.0.2.dev007-py2.4-win32.egg")))
        self.assertFalse(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
        
    
    # -------------------------------------------
    # Test upgrading a package
    # -------------------------------------------    
    def test_upgrade(self):
        self.session.install(["foo==0.0.1.dev007"])     
        self.session.install(["foo"])
        
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "foo-0.0.2.dev007-py2.4-win32.egg")))
        self.assertFalse(self._search_easy_install_pth("foo-0.0.1.dev006-py2.4-win32.egg"))
        self.assertTrue(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
        
    
    # -------------------------------------------
    # Test listiing of installed packages
    # -------------------------------------------
    def test_installed_list(self):
        self.session.install(["foo", "bar", "baz"])
        inst_pkgs = self.session.get_installed_packages()
        
        self.assertTrue(self._search_pkg_obj_list("foo", "0.0.2.dev007", inst_pkgs))
        self.assertTrue(self._search_pkg_obj_list("bar", "2.0.0", inst_pkgs))
        self.assertTrue(self._search_pkg_obj_list("baz", "0.0.7", inst_pkgs))
        
    
    # -------------------------------------------
    # Test listing of upgradable packages
    # -------------------------------------------    
    def test_upgrade_list(self):
        self.session.install(["foo==0.0.1.dev007"])     
        up_pkgs = self.session.get_upgrade_packages()
        self.assertTrue(self._search_pkg_obj_list("foo", "0.0.2.dev007", up_pkgs))
        
        
    # -------------------------------------------
    # Test listing of packages in repository
    # -------------------------------------------
    def test_repo_list(self):
        repo_pkgs = self.session.get_repository_packages()
                    
        self.assertTrue(self._search_pkg_obj_list("foo", "0.0.2.dev007", repo_pkgs))
        self.assertTrue(self._search_pkg_obj_list("foo", "0.0.1.dev007", repo_pkgs))
        self.assertTrue(self._search_pkg_obj_list("foo", "0.0.1.dev006", repo_pkgs))
        self.assertTrue(self._search_pkg_obj_list("bar", "2.0.0", repo_pkgs))
        self.assertTrue(self._search_pkg_obj_list("baz", "0.0.7", repo_pkgs))
        
        
    # -------------------------------------------
    # Test the deactivation of a package
    # -------------------------------------------
    def test_deactivate(self):
        self.session.install(["foo", "bar", "baz"])
        inst_pkgs = self.session.get_installed_packages()
        pkg_to_deactivate = self._search_pkg_obj_list("foo", "0.0.2.dev007", inst_pkgs)
        self.session.deactivate(pkg_to_deactivate)
        
        self.assertFalse(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "foo-0.0.2.dev007-py2.4-win32.egg")))
        
    
    # -------------------------------------------
    # Test the activation of a package
    # -------------------------------------------   
    def test_activate(self):
        self.session.install(["foo==0.0.1.dev007", "foo==0.0.2.dev007"])
        
        inst_pkgs = self.session.get_installed_packages()
        pkg_to_deactivate = self._search_pkg_obj_list("foo", "0.0.2.dev007", inst_pkgs)
        pkg_to_activate = self._search_pkg_obj_list("foo", "0.0.1.dev007", inst_pkgs)
        self.session.deactivate(pkg_to_deactivate)
        self.session.activate(pkg_to_activate)
        
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "foo-0.0.2.dev007-py2.4-win32.egg")))
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "foo-0.0.1.dev007-py2.4-win32.egg")))
        
        self.assertFalse(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
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
    
    
    # -------------------------------------------------------
    # Helper function to search though a list of Package objs
    # -------------------------------------------------------
    def _search_pkg_obj_list(self, package_name, package_version, pkg_objs = []):
        
        for pkg in pkg_objs:
            if pkg.name == package_name:
                if pkg.version == package_version:
                    return pkg
        
        return False

        
if( __name__ == "__main__" ) :
    unittest.main()
