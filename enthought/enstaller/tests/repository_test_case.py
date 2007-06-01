#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Deepu Sudhakar - 2007-03-13
#------------------------------------------------------------------------------

import os
import sys
from os import path
import unittest

from enstaller.repository_factory import \
     create_repository
from enstaller.package import Package
from enthought.testing import api

from enthought.traits.api import \
     HasTraits, TraitError

# Tests the Repository functionality of Enstaller
# Since repos depends on Package objs, this can also serve as testing for Package

CURRENT_DIR = path.abspath(path.dirname(__file__))

ENTHOUGHT_REPO = "http://code.enthought.com/enstaller/eggs/"
LOCAL_REPO = path.abspath(path.join(CURRENT_DIR, "test_repo"))
PYPI_REPO = "http://python.org/pypi"

class RepositoryTestCase( unittest.TestCase ) :

    def __init__( self, *args ) :
        super( RepositoryTestCase, self ).__init__( *args )
        
        class RemoteRepositoryTester(HasTraits):
            r = create_repository(ENTHOUGHT_REPO, False, False, sys.stdout)
        
        class LocalRepositoryTester(HasTraits):
            r = create_repository(LOCAL_REPO, False, False, sys.stdout)
        
        class PypiRepositoryTester(HasTraits):
            r = create_repository(PYPI_REPO, False, False, sys.stdout)
        
        self.remote_repo_tester = RemoteRepositoryTester()
        self.local_repo_tester = LocalRepositoryTester()
        self.pypi_repo_tester = PypiRepositoryTester()
        
    
    # -----------------------------------------------------
    # Write a dummy easy-install.pth file in the local repo
    # -----------------------------------------------------    
    def setUp(self):
        f = open(path.join(LOCAL_REPO, "easy-install.pth"), 'w')
        f.write("import sys; sys.__plen = len(sys.path)\n")
        f.write("./bar-2.0.0-py2.4-win32.egg\n")
        f.write("./foo-0.0.1.dev007-py2.4-win32.egg\n")
        f.write("./baz-0.0.7-py2.4-win32.egg\n")
        f.write("import sys; new=sys.path[sys.__plen:]; del sys.path[sys.__plen:]; p=getattr(sys,'__egginsert',0); sys.path[p:p]=new; sys.__egginsert = p+len(new))")
        f.close()
    
    
    # --------------------------------------
    # Remove our dummy easy-install.pth file
    # --------------------------------------
    def tearDown(self):
        os.remove(path.join(LOCAL_REPO, "easy-install.pth"))
        
    
    # ------------------------------
    # List the eggs in a remote repo
    # ------------------------------
    def test_remote_repo_list(self):
        self.remote_repo_tester.r.build_package_list()
        
        for package in self.remote_repo_tester.r.packages:
            self.failUnless(isinstance(package, Package))
    
    
    # ------------------------------
    # Find an egg in a remote repo
    # ------------------------------
    def test_remote_repo_find_package(self):
        package_to_find = "enstaller"
        
        self.remote_repo_tester.r.build_package_list()
        packages = self.remote_repo_tester.r.find_packages([package_to_find])
        
        for package in packages:
            self.failUnless(package.name == package_to_find)
            
            
    # -----------------------------------
    # Find multiple eggs in a remote repo
    # -----------------------------------
    def test_remote_repo_find_packages(self):
        packages_to_find = ["numpy", "scipy", "enstaller"]

        self.remote_repo_tester.r.build_package_list()
        packages = self.remote_repo_tester.r.find_packages(packages_to_find)
        
        for package in packages:
            self.failIf(package.name not in packages_to_find)

            
    # ----------------------------------------
    # Find a non-existent egg in a remote repo
    # ----------------------------------------
    def test_remote_repo_find_package_not_existing(self):
        package_to_find = "foobar"
        
        self.remote_repo_tester.r.build_package_list()
        packages = self.remote_repo_tester.r.find_packages([package_to_find])
        
        self.failUnless(len(packages) == 0)
        
    
    # ----------------------------------------
    # Find non-existent eggs in a remote repo
    # ----------------------------------------
    def test_remote_repo_find_packages_not_existing(self):
        packages_to_find = ["numpy", "scipy", "foobar"]
        
        self.remote_repo_tester.r.build_package_list()
        packages = self.remote_repo_tester.r.find_packages(packages_to_find)
        
        for package in packages:
            self.failIf(package.name not in packages_to_find)
            

    # ------------------------------
    # List the eggs in a local repo
    # ------------------------------
    def test_local_repo_list(self):
        self.local_repo_tester.r.build_package_list()
        
        for package in self.local_repo_tester.r.packages:
            self.failUnless(isinstance(package, Package))
            
    
    # ------------------------------
    # Find an egg in a local repo
    # ------------------------------
    def test_local_repo_find_package(self):
        package_to_find = "foo"
        
        self.local_repo_tester.r.build_package_list()
        packages = self.local_repo_tester.r.find_packages([package_to_find])
        
        for package in packages:
            self.failUnless(package.name == package_to_find)
            
    
    # ----------------------------------------
    # Find a non-existent egg in a local repo
    # ----------------------------------------
    def test_local_repo_find_package_not_existing(self):
        package_to_find = "foobar"
        
        self.local_repo_tester.r.build_package_list()
        packages = self.local_repo_tester.r.find_packages([package_to_find])
        
        self.failUnless(len(packages) == 0)
        
    
    # ----------------------------------------
    # Find multiple eggs in a local repo
    # ----------------------------------------
    def test_local_repo_find_packages(self):
        packages_to_find = ["foo", "bar", "baz"]
        
        self.local_repo_tester.r.build_package_list()
        packages = self.local_repo_tester.r.find_packages(packages_to_find)
        
        for package in packages:
            self.failIf(package.name not in packages_to_find)
    
    
    # ----------------------------------------
    # Find non-existent eggs in a local repo
    # ----------------------------------------
    def test_local_repo_find_packages_not_existing(self):
        packages_to_find = ["foo", "bar", "foobar"]
        
        self.local_repo_tester.r.build_package_list()
        packages = self.local_repo_tester.r.find_packages(packages_to_find)
        
        for package in packages:
            self.failIf(package.name not in packages_to_find)
    
    
    # -------------------------------------------
    # Check metadata on an egg in a local repo
    # -------------------------------------------
    def test_local_repo_find_package_metadata(self):
        package_name = "bar"
        package_version = "2.0.0"
        package_py_ver = "py2.4"

        self.local_repo_tester.r.build_package_list()
        package_objs = self.local_repo_tester.r.find_packages([package_name])
        
        for package in package_objs:
            self.assertEqual(package.name, package_name)
            self.assertEqual(package.version, package_version)
            self.assertEqual(package.py_version, package_py_ver)
    
    
    # --------------------------------------------
    # Retrieve list of active eggs in installation 
    # --------------------------------------------
    def test_local_repo_get_active(self):
        should_be_active = ["bar-2.0.0-py2.4-win32.egg", 
                            "foo-0.0.1.dev007-py2.4-win32.egg", 
                            "baz-0.0.7-py2.4-win32.egg"]

        
        self.local_repo_tester.r.build_package_list()
        active = self.local_repo_tester.r.get_active_packages()
        
        for package in active:
            self.failIf(package.fullname not in should_be_active)
            
    
    # ----------------------------------------
    # Check if package is active (should be)
    # ----------------------------------------
    def test_local_repo_is_active_yes(self):
        should_be_active = "foo-0.0.1.dev007-py2.4-win32.egg"
        
        self.local_repo_tester.r.build_package_list()
        active = self.local_repo_tester.r.is_package_active(should_be_active)

        self.assertEquals(active, True)
            
    
    # ------------------------------------------
    # Check if package is active (should not be)
    # ------------------------------------------
    def test_local_repo_is_active_no(self):
        should_be_active = "foo-0.0.1.dev006-py2.4-win32.egg"
        
        self.local_repo_tester.r.build_package_list()
        active = self.local_repo_tester.r.is_package_active(should_be_active)

        self.assertEquals(active, False)
        
    # -----------------------------------------
    # Set eggs to active or inactive
    # -----------------------------------------
    def test_local_repo_toggle_active(self):
        packages = ["bar-2.0.0-py2.4-win32.egg",
                    "foo-0.0.1.dev007-py2.4-win32.egg",
                    "foo-0.0.1.dev006-py2.4-win32.egg"]
        
        self.local_repo_tester.r.build_package_list()
           
        self.local_repo_tester.r.toggle_packages_active_state(packages)
        
        self.assertEquals(self.local_repo_tester.r.is_package_active("numpy-1.0.2.dev3572-py2.4-win32.egg"), False)
        self.assertEquals(self.local_repo_tester.r.is_package_active("foo-0.0.1.dev007-py2.4-win32.egg"), False)
        self.assertEquals(self.local_repo_tester.r.is_package_active("foo-0.0.1.dev006-py2.4-win32.egg"), True)
        
    
    # ------------------------------
    # List the eggs in a Pypi repo
    # ------------------------------
    def test_pypi_repo_list(self):
        self.pypi_repo_tester.r.build_package_list()
        
        for package in self.pypi_repo_tester.r.packages:
            self.failUnless(isinstance(package, Package))
      
            
    # -------------------------------------------
    # List certain eggs from Pypi
    # -------------------------------------------
    def test_pypi_repo_find_package(self):
        package_to_find = "numpy"
        
        #self.pypi_repo_tester.r.build_package_list()
        packages = self.pypi_repo_tester.r.find_packages([package_to_find])
        
        for package in packages:
            self.failUnless(package.name == package_to_find)
            
    
    # -------------------------------------------
    # Find multiple eggs in Pypi
    # -------------------------------------------
    def test_pypi_repo_find_packages(self):
        packages_to_find = ["numpy", "scipy"]
        
        #self.pypi_repo_tester.r.build_package_list()
        packages = self.pypi_repo_tester.r.find_packages(packages_to_find)
        
        for package in packages:
            self.failIf(package.name not in packages_to_find)




if( __name__ == "__main__" ) :
    unittest.main()
