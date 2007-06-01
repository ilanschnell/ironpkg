#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Deepu Sudhakar - 2007-03-22
#------------------------------------------------------------------------------

import unittest
import shutil
import os

from os import path

from enstaller.enstaller_session import \
     EnstallerSession
from enstaller.enstaller_cli import \
     EnstallerCLI
from enstaller.enstaller_logger import \
     EnstallerLogger
     
from enthought.traits.api import \
     HasTraits, TraitError

# Convenient global variables specifying dir locations
CURRENT_DIR = path.abspath(path.dirname(__file__))
LOCAL_REPO = path.normcase(path.abspath(path.join(CURRENT_DIR, "test_repo")))
INSTALL_DIR = path.normcase(path.abspath(path.join(CURRENT_DIR, "install")))


# ----------------------------------------------------------------
# Test case for EnstallerCLI and associated operations.
# ----------------------------------------------------------------
class EnstallerCLITestCase( unittest.TestCase ) :
    
    
    def __init__( self, *args ) :
        super( EnstallerCLITestCase, self ).__init__( *args )
        
    
    # -------------------------------------------
    # Set up a logger, session, and CLI instance
    # -------------------------------------------          
    def setUp(self):
        
        # Instantiate a logger to capture stdout
        self.write = Write()
        logger = EnstallerLogger(targets = [self.write])
        
        self.session = EnstallerSession(find_links = [LOCAL_REPO],
                                        install_dir = INSTALL_DIR,
                                        logging_handle = logger)
        self.session.initialize()
        
        self.cli = EnstallerCLI(session = self.session,
                                logging_handle = logger)
        
    
    # -------------------------------------------
    # Remove the dummy install after each test
    # ------------------------------------------- 
    def tearDown(self):
        shutil.rmtree(INSTALL_DIR)
    
    
    # -------------------------------------------
    # Test installing a package through CLI
    # -------------------------------------------
    def test_install(self):
        self.cli.install(INSTALL_DIR, ["foo"])

        self.assertTrue(path.exists(path.join(INSTALL_DIR, "foo-0.0.2.dev007-py2.4-win32.egg")))
        self.assertTrue(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
        
    
    # -------------------------------------------
    # Test removing a package through CLI
    # -------------------------------------------    
    def test_remove(self):
        self.cli.install(INSTALL_DIR, ["foo"])      
        self.cli.remove(["foo"])
        
        self.assertFalse(path.exists(path.join(INSTALL_DIR, "foo-0.0.2.dev007-py2.4-win32.egg")))
        self.assertFalse(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
        
    
    # -------------------------------------------
    # Test upgrading a package through CLI
    # -------------------------------------------    
    def test_upgrade(self):
        self.cli.install(INSTALL_DIR, ["foo==0.0.1.dev006"])
        self.cli.upgrade(INSTALL_DIR, ["foo"])
        
        self.assertTrue(path.exists(path.join(INSTALL_DIR, "foo-0.0.2.dev007-py2.4-win32.egg")))
        self.assertFalse(self._search_easy_install_pth("foo-0.0.1.dev006-py2.4-win32.egg"))
        self.assertTrue(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
    
    
    # -------------------------------------------------
    # Test the output of listing all installed packages
    # -------------------------------------------------
    def test_list_installed(self):
        
        # The following would have been a convenient way to compare outputs.
        # However, the package list may list packages outside out dummy install
        
        #exp_output = ""
        #exp_output += "------------------------------------------------------------\n"
        #exp_output += "name | version      | act | location\n"
        #exp_output += "------------------------------------------------------------\n"
        #exp_output += "bar  | 2.0.0        |  Y  | %s\n"
        #exp_output += "foo  | 0.0.2.dev007 |  Y  | %s\n"
        #exp_output += "baz  | 0.0.7        |  Y  | %s\n"
        #
        #exp_output = exp_output % (INSTALL_DIR, INSTALL_DIR, INSTALL_DIR)
        #self.cli.install(INSTALL_DIR, ["bar", "foo", "baz"])
        #self.cli.list_installed()
        
        #act_output = self.write.message
        
        self.cli.install(INSTALL_DIR, ["bar", "foo", "baz"])
        self.cli.list_installed()
        
        # Read the output from logger
        act_output = self.write.message
        
        # Ugly workaround to parse the logger output
        lines = act_output.split("\n")
        lines = lines[3:-1]
        
        inst_p = [] # Will contain list of install package names
        for line in lines:
            cats = line.split("|")
            installed = "%s-%s" % (cats[0].strip(), cats[1].strip())
            inst_p.append(installed)
            
        self.assertTrue("bar-2.0.0" in inst_p)
        self.assertTrue("foo-0.0.2.dev007" in inst_p)
        self.assertTrue("baz-0.0.7" in inst_p)
        
    
    # ------------------------------------------------
    # Test the output of listing all possible upgrades
    # ------------------------------------------------
    def test_list_upgrades(self):
        exp_output = ""
        exp_output += "------------------------------------------------------------\n"
        exp_output += "name | version      | inst | location\n"
        exp_output += "------------------------------------------------------------\n"
        exp_output += "foo  | 0.0.2.dev007 |   n  | %s\n"
        
        exp_output = exp_output % (LOCAL_REPO)
        
        self.cli.install(INSTALL_DIR, ["foo==0.0.1.dev006"])
        self.cli.list_upgrades(INSTALL_DIR, ["foo"])
        
        act_output = self.write.message
        
        self.assertEquals(act_output, exp_output)
       
    
    # -------------------------------------------------------
    # Test the output of listing all packages in a repository
    # -------------------------------------------------------
    def test_list_repos(self):
        exp_output = ""
        exp_output += "------------------------------------------------------------\n"
        exp_output += "name | version      | inst | location\n"
        exp_output += "------------------------------------------------------------\n"
        exp_output += "bar  | 2.0.0        |   n  | %s\n"
        exp_output += "baz  | 0.0.7        |   n  | %s\n"
        exp_output += "foo  | 0.0.1.dev006 |   n  | %s\n"
        exp_output += "foo  | 0.0.1.dev007 |   n  | %s\n"
        exp_output += "foo  | 0.0.2.dev007 |   n  | %s\n"
        
        exp_output = exp_output % (LOCAL_REPO, LOCAL_REPO, LOCAL_REPO, LOCAL_REPO, LOCAL_REPO)

        self.cli.list_repos()
        
        act_output = self.write.message
        
        self.assertEquals(act_output, exp_output)
    
    
    # -------------------------------------------
    # Test the deactivation of a package
    # -------------------------------------------
    def test_deactivate(self):
        self.cli.install(INSTALL_DIR, ["foo", "bar", "baz"])
        self.cli.deactivate(["foo"])
        
        self.assertFalse(self._search_easy_install_pth("foo-0.0.2.dev007-py2.4-win32.egg"))
        
    
    # -------------------------------------------
    # Test the activation of a package
    # -------------------------------------------   
    def test_activate(self):
        self.cli.install(INSTALL_DIR, ["foo==0.0.1.dev007", "foo==0.0.2.dev007"])
        self.cli.deactivate(["foo==0.0.2.dev007"])
        self.cli.activate(["foo==0.0.1.dev007"])
        
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


# --------------------------------------------
# Class that acts a simple log handler.
# Stores output from EnstallerCLI as paramater
# --------------------------------------------        
class Write:
    message = ""
    
    def write(self, msg):
        self.message = msg
        
    def flush(self):
        self.message = ""
        
        
if( __name__ == "__main__" ) :
    unittest.main()
