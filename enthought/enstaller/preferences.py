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

import re
from types import ListType

from enthought.traits.api import \
     HasTraits, List, Str, Bool, Property, Instance

from enthought.traits.ui.api import \
     View, Group, HGroup, Item, \
     TextEditor, FileEditor, DirectoryEditor


################################################################################
## Helper functions for converting data read from text files to Python objects
## and back to text.
################################################################################

def config_value_to_list_of_strings( self, config_value ) :
    los = re.split( r"[,\ \n]+", config_value )
    if( los == [""] ) :
        los = []
    return los

def config_value_to_bool( self, config_value ) :
    if( config_value.lower() == "true" ) :
        return True
    elif( config_value.lower() == "false" ) :
        return False

def list_of_strings_to_config_value( self, los ) :
    return ", ".join( ["%s" % s for s in los] )

def other_to_config_value( self, val ) :
    return "%s" % val



################################################################################
## The Preference family of classes.
################################################################################

class Preference( HasTraits ) :
    """
    Base class for all Enstaller preference objects.

    Each object has a specific value type, view, and help description.
    """
    #
    # The property name, derived from the class name via a property getter
    #
    name = Property

    #
    # The section in the config file, used for writing the values back to
    # the right place in the config files.
    #
    section = Str

    #
    # The descriotion, mainly used for help
    #
    description = Str

    #
    # The (short) text show to the user describing what the preference is for.
    #
    label = Str

    #
    # The actual value...type is overridden by subclasses.
    #
    value = Str

    #
    # Conversion functions (overridden in subclasses):
    # Convert to py simply returns the value (already a Py type)
    # Convert to config maps to a conversion helper function to convert the
    #  py type to a string for a config file.
    #
    convert_to_py_type = classmethod( lambda self, val: val )
    convert_to_config_type = classmethod( other_to_config_value )

    #
    # Flag indicating value was changed and needs to be saved.
    #
    modified = Bool

    #
    # The default view for a preference.
    #
    traits_view = View(
        Group(
            HGroup( 
               Item( name="label",
                     show_label=False,
                     style="readonly",
                     ),
               Item( name="value",
                     show_label=False,
                     style="custom",
                     ),),
           Item( name="description",
                 show_label=False,
                 style="readonly",
                 ),
           show_border=True,
           ),
        )


    def update_config( self, config_obj ) :
        """
        Updates a config object (an instance of a RawConfigParser) in the
        config section with the current value.
        """
        if( self.modified ) :
            if( not( config_obj.has_section( self.section ) ) ) :
                config_obj.add_section( self.section )
                
            config_obj.set( self.section, self.name,
                            self.convert_to_config_type( self.value ) )

            return True

        return False


    #############################################################################
    # Traits handlers, defaults, etc.
    #############################################################################

    def _get_name( self ) :
        """
        Getter for name property...examines the class name to return pref. name.
        """
        name = self.__class__.__name__
        name = name[0].lower() + name[1:]
        name = re.sub( r"([A-Z])", r"_\1", name )
        name = name.lower()
        return name


    def _value_changed( self ) :
        """
        Mark this preference object if the value changed so it can be written
        back to the config file.
        """
        self.modified = True



################################################################################
## The individual preference classes for each preference used by Enstaller.
################################################################################
        
class EasyInstallPreference( Preference ) :
    """
    Base class for all preferences for easy_install.
    """
    section = Str( "easy_install" )


class EnstallerPreference( Preference ) :
    """
    Base class for all preferences for Enstaller.
    """
    section = Str( "enstaller" )


class ShowAllAvailableVersions( EnstallerPreference ) :
    value = Bool
    label = "Show all available versions:"
    convert_to_py_type = classmethod( config_value_to_bool )
    description = Str( \
"""For each package, show every version that is available for installation .""" )


class FindLinks( EasyInstallPreference ) :
    value = List()
    label = "Repository URLs:"
    convert_to_py_type = classmethod( config_value_to_list_of_strings )
    convert_to_config_type = classmethod( list_of_strings_to_config_value )
    description = Str( \
"""Find packages using the URLs specified in this list. The default URL, 
<http://code.enthought.com/enstaller/eggs>, is always used.
""" )

    traits_view = View(
        Group(
            HGroup( 
               Item( name="label",
                     show_label=False,
                     style="readonly",
                     ),
               Item( name="value",
                     show_label=False,
                     style="simple",
                     resizable = True,
                     height = 100,
                     width = 300
                     ),),
           Item( name="description",
                 show_label=False,
                 style="readonly",
                 ),
           show_border=True,
           ),
        )


class AllowHosts( EasyInstallPreference ) :
    value = List( Str )
    label = "Restrict repository URLs to:"
    convert_to_py_type = classmethod( config_value_to_list_of_strings )
    convert_to_config_type = classmethod( list_of_strings_to_config_value )
    same_as_find_links = Bool
    find_links = Instance( FindLinks )
    allow_hosts_value = List( Str )
    description = Str( \
"""Restricts downloading and spidering to hosts matching the specified glob 
patterns.  For example, "*.python.org" restricts web access so that only 
packages from machines in the python.org domain are  listed and downloadable.
The glob patterns must match the entire user/host/port section of the target 
URL(s). For example, '*.python.org' does NOT allow a URL like 
'http://python.org/foo' or 'http://www.python.org:8080/'. The default pattern 
is '*', which matches anything.
""" )
    traits_view = View(
        Group(
            HGroup(
               Item( name="label",
                     show_label=False,
                     style="readonly",
                     ),
               Item( name="value",
                     show_label=False,
                     style="custom",
                     ),),
           Group(
              Item( name="same_as_find_links",
                    label="Only allow hosts specified in Repository URLs (above)",
                    ),
              ),
           Item( name="description",
                 show_label=False,
                 editor=TextEditor(),
                 style="readonly",
                 ),
           show_border=True,
           ),
        )

    def _same_as_find_links_changed( self, old, new ) :
        if( new == True ) :
            if( len( self.allow_hosts_value ) == 0 ) :
                self.allow_hosts_value = self.value
            self.value = self.find_links.value
        else :
            self.value = self.allow_hosts_value


class AlwaysUnzip( EasyInstallPreference ) :
    value = Bool
    label = "Always unzip packages:"
    convert_to_py_type = classmethod( config_value_to_bool )
    description = Str( \
"""Do not install any packages as zip files, even if the packages are marked as
safe for running as a zip file. This option is useful if an egg does something 
unsafe, but not in a way that can be detected when the egg was built. Use this 
option only if you have had problems with a particular egg. 

NOTE: This option affects the installation only of newly built or downloaded 
packages that are not already installed; if you want to convert an existing 
installed version from zipped to unzipped or vice versa, delete the existing 
version, and then re-install it after changing this option.""" )

    
class ScriptDir( EasyInstallPreference ) :
    value = Str
    label = "Script installation directory:"
    description = Str( \
"""This option defaults to the install directory, so that the scripts can find 
their associated package installations. Otherwise, this setting defaults to the 
location where the distutils would normally install scripts, taking any 
distutils configuration file settings into account.
""" )
    traits_view = View(
        Group(
           Item( name="label",
                 show_label=False,
                 style="readonly",
                 ),
           Item( name="value",
                 show_label=False,
                 editor=DirectoryEditor(),
                 ),
           Item( name="description",
                 show_label=False,
                 editor=TextEditor(),
                 style="readonly",
                 ),
           show_border=True,
           ),
        )

class ExcludeScripts( EasyInstallPreference ) :
    value = Bool
    label = "Do not install scripts:"
    convert_to_py_type = classmethod( config_value_to_bool )
    description = Str( \
"""This option is useful if you need to install multiple versions of a package, 
but do not want to reset the version that will be run by scripts that are 
already installed.
""" )

class Record( EasyInstallPreference ) :
    value = Str
    label = "Record files to:"
    description = Str( \
"""Write a record of all installed files to the file specified by this option. 
This option is basically the same as the option for the standard distutils
'install' command, and is included for compatibility with tools that expect to
pass this option to 'setup.py install'.
""" )
    traits_view = View(
        Group(
           Item( name="label",
                 show_label=False,
                 style="readonly",
                 ),
           Item( name="value",
                 show_label=False,
                 editor=FileEditor(),
                 ),
           Item( name="description",
                 show_label=False,
                 editor=TextEditor(),
                 style="readonly",
                 ),
           show_border=True,
           ),
        )
