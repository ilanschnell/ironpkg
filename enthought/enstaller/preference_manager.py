#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2006-06-21
#------------------------------------------------------------------------------

from os import path
import re
from ConfigParser import \
     RawConfigParser

from setuptools.command.setopt import \
     config_file

from enthought.traits.api import \
     HasTraits, List, Str, Instance

from enthought.enstaller.preferences import \
     AllowHosts, AlwaysUnzip, ExcludeScripts, FindLinks, Record, \
     ScriptDir, ShowAllAvailableVersions

    
class PreferenceManager( HasTraits ) :
    """
    Class which maintains the relevant user preferences for Enstaller.

    The preferences are loaded from the same config files used by distutils
    and setuptools.
    """
    #
    # these traits represent the known preferences supported
    #
    allow_hosts = Instance( AllowHosts, () )
    always_unzip = Instance( AlwaysUnzip, () )
    exclude_scripts = Instance( ExcludeScripts, () )
    find_links = Instance( FindLinks, () )
    show_all_available_versions = Instance( ShowAllAvailableVersions, () )
    record = Instance( Record, () )
    script_dir = Instance( ScriptDir, () )

    #
    # Maintain an easy-to-reference list of all the known preferences.
    #
    known_prefs = List( Str )

    #
    # The config object is a base config file parser.
    # The others are individual config files shared by setuptools.
    # Instantiate these by default for each instance of a PreferenceManager
    #
    config = Instance( RawConfigParser, () )
    site_pref_file = Str( config_file( "global" ) )
    user_pref_file = Str( config_file( "user" ) )
    local_pref_file = Str( config_file( "local" ) )


    def read( self ) :
        """
        Read the config files and set the corresponding attributes on this obj.
        """
        self.config.read( [self.site_pref_file,
                           self.user_pref_file,
                           self.local_pref_file] )

        for section in self.config.sections() :
            for (option, raw_value) in self.config.items( section ) :
                #
                # strip any inline comments in the config file
                #
                raw_value = re.split( "#", raw_value, maxsplit=1 )[0]

                if( option in self.known_prefs ) :
                    cls = getattr( self, option ).__class__
                    value = cls.convert_to_py_type( raw_value )
                    setattr( self, option, cls( value=value ) )

         #
         # special case...let allow_hosts know about find_links
         #
         #self.allow_hosts.find_links = self.find_links
        

    def write( self ) :
        """
        Write the preferences stored as attributes on this object to the
        user's config file.
        """
        #
        # update the config object with any changes from the known
        # preferences...the preference objects update the config object
        # since they know the ocnfig section, etc.
        #
        val_changed = False

        for pref in self.known_prefs :
            if( self.get( pref )[pref].update_config( self.config ) ) :
                val_changed = True
        #
        # write the new config file if any value changed
        #
        if( val_changed ) :
            pref_file_handle = open( self.user_pref_file, "wu" )
            self.config.write( pref_file_handle )
            pref_file_handle.close()


    #############################################################################
    # Traits handlers, defaults, etc.
    #############################################################################

    def _known_prefs_default( self ) :
        """
        The default list of known preferences.
        """
        return [
            "allow_hosts",
            "always_unzip",
            "exclude_scripts",
            "find_links",
            "show_all_available_versions",
            "record",
            "script_dir",
            ]
    

