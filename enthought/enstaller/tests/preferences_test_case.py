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
import unittest
import shutil
import tempfile

from setuptools.command.setopt import \
     config_file
     
from enstaller.preference_manager import PreferenceManager

from enthought.traits.api import \
     HasTraits, TraitError


class PreferencesTestCase( unittest.TestCase ) :
    
    # ---------------------------------------------------
    # Retrieve the locations of setuptools's config files
    # ---------------------------------------------------
    site_pref_file = config_file( "global" )
    user_pref_file = config_file( "user" )
    local_pref_file = config_file( "local" )
    
    # ---------------------------------------------------
    # Create temp files to store these config files
    # ---------------------------------------------------
    (site_fd, site_pref_temp_file) = tempfile.mkstemp()
    (user_fd, user_pref_temp_file) = tempfile.mkstemp()
    (local_fd, local_pref_temp_file) = tempfile.mkstemp()
    
    
    # ------------------------------------------------
    # Map the config files to temporary locations
    # ------------------------------------------------
    file_map = {site_pref_file : site_pref_temp_file,
                user_pref_file : user_pref_temp_file,
                local_pref_file : local_pref_temp_file}
    

    def __init__( self, *args ) :
        super( PreferencesTestCase, self ).__init__( *args )
        
        self.pref_man_tester = PreferenceManager()
        
        
    def setUp(self):
        # Copy the config files to the temp locations
        for file in self.file_map.keys():
            try:
                shutil.copy(os.path.abspath(file), os.path.abspath(self.file_map[file]))
                os.remove(os.path.abspath(file))
            except:
                # Ignore exceptions since conf file may not exist (harmless)
                "Do Nothing"
            
            
    def tearDown(self):
        # Copy the the temp files back to the config locations
        for file in self.file_map.keys():
            try:
                os.remove(os.path.abspath(file))
                shutil.copy(os.path.abspath(self.file_map[file]), os.path.abspath(file))
                os.remove(os.path.abspath(self.file_map[file]))
            except:
                # Ignore exceptions since conf file may not exist (harmless)
                "Do Nothing"
                
    
    # ----------------------------------------------------
    # Tests the reading abilities of the PreferenceManager    
    # ----------------------------------------------------
    def test_pref_file_read(self):
        # Prefs to test with
        prefs = {"allow_hosts" : ["*.python.org"],
                 "always_unzip" : True,
                 "exclude_scripts" : False,
                 "find_links" : ["pypi.python.org", "testing.python.org"],
                 "show_all_available_versions" : False,
                 "record" : "./bar.txt",
                 "script_dir" : "./foo"}
        
        # Create a dummy config file to parse later
        for file in self.file_map.keys():
            f = open(os.path.abspath(file), 'w')
            f.write("[easy_install]\n")
            f.write("always_unzip = True\n")
            f.write("record = ./bar.txt\n")
            f.write("script_dir = ./foo\n")
            f.write("allow_hosts = *.python.org\n")
            f.write("find_links = pypi.python.org, testing.python.org\n")
            f.close()
        
        # Parse config file
        self.pref_man_tester.read()
        
        # Check to see if config file matches pre-selected prefs
        for key in prefs.keys():
            self.assertEqual(self.pref_man_tester.get(key)[key].value, prefs[key])
        
        
            
    def test_pref_file_write(self):
        # Prefs to test with
        prefs = {"allow_hosts" : ["*.foo.org"],
                 "exclude_scripts" : True,
                 "always_unzip" : True,
                 "find_links" : ["bar.foo.org", "baz.foo.org"],
                 "show_all_available_versions" : False,
                 "record" : "./foo.txt",
                 "script_dir" : "./bar"}
        
        # Write each pref key to the PreferenceManager
        for key in prefs.keys():
            self.pref_man_tester.get(key)[key].value = prefs[key]
    
        self.pref_man_tester.write()
        
        # Read back the prefereneces
        self.pref_man_tester.read()
        
        # Check to see if config file matches pre-selected prefs
        for key in prefs.keys():
            self.assertEquals(self.pref_man_tester.get(key)[key].value, prefs[key])


if( __name__ == "__main__" ) :
    unittest.main()
