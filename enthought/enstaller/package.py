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

import sys
from os import path
import re
import platform

from pkg_resources import \
     parse_requirements, Requirement

from enthought.traits.api import \
     HasTraits, List, Str, Enum, Bool, Int, Property

from enthought.enstaller.api import \
     IS_WINDOWS
from enthought.enstaller.downloader import \
     Downloader
from enthought.enstaller.egg import \
     Egg

version_cmp = Downloader.version_cmp


class Package( HasTraits ) :
    """
    Class which contains information about a Python package
    """
    #
    # Attributes available for a package
    #
    name = Str
    raw_version = Str
    version = Str
    build = Int
    stable_version = Str
    py_version = Enum( "", "py2.4", "py2.5", "py2.3", "py2.6" )
    author = Str
    author_email = Str
    maintainer = Str
    maintainer_email = Str
    home_page = Str
    license = Str
    summary = Str
    description = Str
    keywords = Str
    platform = Str
    download_url = Str
    info_url = Str
    classifiers = List( Str )

    #
    # Either a path on disk or a URL where the package is installed/downloaded
    #
    location = Str

    #
    # The "full" name of the package with all info from the filename
    # (foo-1.2-py2.4-win32)
    #
    fullname = Str

    #
    # A list of requirement strings, as seen in a .info file
    #
    depends = List

    #
    # The list of requirement objs used for checking
    #
    requires = List( Requirement )

    #
    # Provides is a list of strings, usually module names
    #
    provides = List( Str )

    #
    # egg_url is used for construction purposes, where if a Package is
    # constructed with egg_url=..., the egg_url trait handler automatically
    # decomposes the egg_url to set other traits
    #
    egg_url = Str

    #
    # Provides a means to make requests back to a containing repository
    #
    repository = None

    #
    # Bool which indicates if the package is active or not
    #
    active = Property
    
    #
    # Flag set to True if meta-data has been set (since fetching it
    # can be expensive)
    #
    meta_data_set = Bool


    def load_meta_data( self ) :
        """
        If a repository for this package is known, then use it to retrieve the
        meta-data for the package.  The repository knows how to access the host
        where the package is kept which may have the meta-data.  This method
        raises an exception if called when a repo is not set.
        """
        #
        # First, if the egg exists on disk, assume the meta-data inside it is
        # what should be used.
        #
        egg_path = path.join( self.location, self.fullname )
        
        if( path.exists( egg_path ) ) :
            self._load_egg_file_meta_data( egg_path )

        #
        # If egg does not exist try reading it remotely (or from a separate file)
        #
        else :
            self._load_remote_meta_data()
            

    def toggle_active_state( self ) :
        """
        Tell the package repository (which is responsible for the pth file
        the package is listed in) to either remove it from the pth file or
        add it back in, thus deactivating/reactivating it
        """
        if( self.repository is None ) :
            raise AssertionError, \
                  "cannot deactivate/reactivate package %s" % self.fullname + \
                  "repository is not known"

        return self.repository.toggle_packages_active_state( self.fullname )


    #############################################################################
    # Protected interface.
    #############################################################################

    def __cmp__( self, package_obj ) :
        """
        Return -1 if self < package_obj, 0 if equal, 1 if self > package_obj,
        or None if cant compare (diff platform, name, etc.)
        """
        comp = 0

        #
        # Try to compare the pacakge names
        #
        if( self.name == package_obj.name ) :

            #
            # If names are equal, try to compare versions
            #
            if( self.version == package_obj.version ) :

                #
                # If versions are equal, compare the pacakge fullnames
                #
                if( IS_WINDOWS ) :
                    this = self.fullname.lower()
                    that = package_obj.fullname.lower()
                else :
                    this = self.fullname
                    that = package_obj.fullname

                comp = cmp( this, that )

            else :
                comp = version_cmp( self.version, package_obj.version )

        else :
            comp = cmp( self.name, package_obj.name )

        return comp


    def _load_egg_file_meta_data( self, egg_path ) :
        """
        Given an egg file, sets the meta-data attrs of this object using the
        meta-data in the egg, if possible.
        """
        egg = Egg( egg_path )

        #
        # Assume the name, version, and build are "more accurate" currently
        # since they were taken from the egg file name directly, so do not
        # include them in the list below.
        #
        for attr in ["stable_version", "py_version", "author", "author_email",
                     "maintainer", "maintainer_email", "home_page", "license",
                     "summary", "description", "keywords", "platform",] :

            if( hasattr( egg, attr ) ) :
                setattr( self, attr, getattr( egg, attr ) )

        self.meta_data_set = True

                     
    def _load_remote_meta_data( self ) :
        """
        Sets the meta-data attrs of this object based on meta-data found on a
        repository server or from a local repo.
        """
        if( self.repository is None ) :
            raise AssertionError, \
                  "cannot read meta-data for %s, repository is not known" \
                  % self.name

        md = ""
        if( hasattr( self.repository, "read_meta_data" ) ) :
            md = self.repository.read_meta_data( self.info_url )

        elif( hasattr( self.repository, "query_meta_data" ) ) :
            md = self.repository.query_meta_data( self.name, self.version )

        if( md ) :
            self._set_meta_data( md )


    def _set_attrs_from_info( self, pkg_info_string ) :
        """
        parses the info string and sets the attributes based on it
        """
        egg_specs = get_egg_specs_from_info( pkg_info_string )
        self.set( **egg_specs )
        return
        try :
            egg_specs = get_egg_specs_from_info( pkg_info_string )
            self.set( **egg_specs )

        except :
            if( len( pkg_info_string ) > 50 ) :
                partial_str = pkg_info_string[0:49]
            else :
                partial_str = pkg_info_string

            print "WARNING: could not parse info string (showing partial): %s"\
                  % partial_str


    def _set_meta_data( self, pkg_info ) :
        """
        sets the package attributes based on the pkg_info string,
        or the dictionary of info
        """
        if isinstance(pkg_info, basestring):
            self._set_attrs_from_info( pkg_info )

        else :
            for (attr, val) in pkg_info.items() :
                if( not( val is None ) and hasattr( self, attr ) ) :
                    setattr( self, attr, val )

        self.meta_data_set = True


    #############################################################################
    # Traits handlers, defaults, etc.
    #############################################################################

    def _depends_changed( self, new ) :
        """
        Update the requires list when the depends list changes
        """
        self.requires = []
        requires_strings = ""

        for dep in new :
            #
            # skip over optional requirements for now (start with [ or ' ')
            #
            if( dep.startswith( "[" ) or dep.startswith( " " ) ) :
                continue
            #
            # otherwsie, assume it is an egg name and make it into a requirmnt
            # (requirement.project_name will end up being the egg name)
            #
            else :
                requires_strings += "%s\n" % dep
        #
        # parse the massive string into a list of requirement objs
        #
        self.requires = list( parse_requirements( requires_strings ) )


    def _egg_url_changed( self, new ) :
        """
        For now, new is a path to an egg (file or dir)

        Set as many package fields as possible using the naming conventions used
        by eggs.  Also, assume egg is a path which can be used to set location,
        meaning it can be a URL or file path.
        """
        (self.location, self.fullname) = path.split( new )
        self.location = path.normcase( self.location )
        egg_specs = get_egg_specs_from_name( self.fullname )
        self.set( **egg_specs )


    def _get_active( self ) :
        """
        Getter for the active flag.
        The packages repository determines if the package is active or not based
        on its presence in the repos pth file...ask the repo if this package is
        active or not.
        """
        is_active = True
        
        if( not( self.repository is None ) and
            hasattr( self.repository, "is_package_active" ) ) :
            is_active = self.repository.is_package_active( self.fullname )

        return is_active



################################################################################
## Free functions related to packages.
## (move to a separate module?)
################################################################################

entry_patt = re.compile( "^([\w\-_]+):\ .*" )

def get_egg_specs_from_info( pkg_info ) :
    """
    Returns a dictionary with as many keys set as possible based on the
    contents of the pkg_info string passed in
    """
    getting_depends = False
    getting_provides = False
    last_key = ""

    specs = {}
    #
    # assume string has attributes separated by newlines
    # ...remove any Windows line ending upfront
    #
    lines = pkg_info.replace( "\r\r\n", "\n" )
    lines = pkg_info.replace( "\r\n", "\n" )

    for line in lines.split( "\n" ) :
        #
        # depends and provides lists have items separated by newlines,
        # lists end when a blank line is encountered
        #
        if( getting_depends ) :
            if( line != "" ) :
                specs["depends"].append( line )
            else :
                getting_depends = False

        elif( getting_provides ) :
            if( line != "" ) :
                specs["provides"].append( line )
            else :
                getting_provides = False

        elif( line.startswith( "Depends:" ) ) :
            getting_depends = True
            specs["depends"] = []

        elif( line.startswith( "Provides:" ) ) :
            getting_provides = True
            specs["provides"] = []
        #
        # if a generic entry, add to the specs dict and remember
        # the key so further lines can be added to it, until another
        # entry is encountered
        #
        elif( entry_patt.match( line ) ) :
            fields = line.split( ": " )
            key = fields[0].lower()
            val = ": ".join( fields[1:] )
            specs[key] = val
            last_key = key
        #
        # add the line to the last key if nothing else matched
        #
        elif( last_key ) :
            specs[last_key] += "\n%s" % line

        #
        # Special case...if a build was not retrieved, check the version string
        # to see if one is in there.
        #
        if( specs.has_key( "version" ) and not( specs.has_key( "build" ) ) ) :
            (raw_ver, ver, build) = get_version_build_tuple( specs["version"] )
            if( not( build is None ) ) :
                specs["raw_version"] = raw_ver
                specs["version"] = ver
                specs["build"] = build
                
    return specs


def get_egg_specs_from_name( egg_name ) :
    """
    Return a dictionary with as many keys set as possible using the naming
    conventions used by eggs:

    <package_name>-<version>_<build>-<py_version>-<platform>.egg
    """
    specs = {}

    if( not( egg_name ) ) :
        return specs

    #
    # use "-" as the delimiter...assume everyone follows that convention
    # when choosing names, version strings, etc.
    #
    allfields = path.splitext( path.basename( egg_name ) )[0].split( "-" )
    allfields.reverse()
    #
    # first field is always the name
    #
    specs["name"] = allfields.pop()

    #
    # second is version...check if build num is in there too
    #
    if( len( allfields ) ) :
        (raw_ver, ver, build) = get_version_build_tuple( allfields.pop() )

        specs["raw_version"] = raw_ver
        specs["version"] = ver

        if( not( build is None ) ) :
            specs["build"] = build

    #
    # third is either py version (must start with py), or platform
    #
    if( len( allfields ) ) :
        val = allfields.pop()
        if( val.startswith( "py" ) ) :
            specs["py_version"] = val
        else :
            specs["platform"] = "-".join( [val] + allfields )
            allfields = []

    #
    # fourth can only be platform
    #
    if( len( allfields ) ) :
        allfields.reverse()
        specs["platform"] = "-".join( allfields )


    return specs


def get_name_from_egg_specs( egg_specs ) :
    """
    Opposite of get_egg_specs_from_name()...returns an egg name based on
    contents of spec dictionary:

    <package_name>-<version>_<build>-<py_version>-<platform>.egg
    """
    egg_name = ""

    if( not( egg_specs ) ) :
        return egg_name

    if( egg_specs.has_key( "name" ) ) :
        egg_name += egg_specs["name"]

        if( egg_specs.has_key( "version" ) ) :
            egg_name += "-%s" % egg_specs["version"]
            if( egg_specs.has_key( "build" ) ) :
                egg_name += "_%s" % egg_specs["build"]

        if( egg_specs.has_key( "py_version" ) ) :
            egg_name += "-%s" % egg_specs["py_version"]

        if( egg_specs.has_key( "platform" ) ) :
            egg_name += "-%s" % egg_specs["platform"]

    return egg_name


def get_version_build_tuple( ver_string ) :
    """
    Return a tuple of (raw_version, version, build_num) based on the ver_string
    passed in.  raw_version is the unmodified version string passed in.  If
    there is no build number, build_num will be None.
    """
    raw_ver = ver_string
    ver = ver_string
    build = None

    #
    # Split on either - or _...build number is last field if an int, otherwise
    # there is no build number.  Version is the rest of the string (or all if
    # no build number).
    #
    vernums = re.split( "([\-\_])", ver_string )

    if( len( vernums ) > 1 ) :
        if( vernums[-1].isdigit() ) :
            ver = "".join( vernums[0:-2] )
            build = int( vernums[-1] )

    return (raw_ver, ver, build)
    

#
# globals used for checking for an installable package
# ...these never change and should not be looked up everytime
#
if( sys.platform.lower().startswith( "linux" ) ) :
    valid_platforms = [sys.platform, "linux"]

    if( platform.machine() != "x86" ) :
        valid_platforms.append( "linux-%s" % platform.machine() )

else :
    valid_platforms = [sys.platform]

py_ver = "py%s.%s" % (sys.version_info[0], sys.version_info[1])


def is_egg_installable( egg_name ) :
    """
    Returns True if egg can be installed on the machine running Enstaller.
    Note: this only check to see if the platform matches, not if user has
    permissions, space, etc.
    Note: this function gets acalled alot...it could be made a little faster
    by saving the results of many of the lookups which dont change.
    """
    specs = get_egg_specs_from_name( egg_name )

    #
    # check the py_version
    #
    if( specs.has_key( "py_version" ) ) :
        if( py_ver != specs["py_version"] ) :
            return False

    #
    # check the architecture
    #
    if( specs.has_key( "platform" ) ) :
        if( not( specs["platform"] in valid_platforms ) ) :
            return False

    return True

