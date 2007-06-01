#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007-02-15
#------------------------------------------------------------------------------

import os
import tempfile
from os import path

from enthought.traits.api import \
     Trait, TraitHandler, Bool
     
from enstaller.run_enstaller import \
     IS_WINDOWS


class UrlTrait( TraitHandler ) :
    """
    Trait used for URLs.
    """

    remote_protocols = ["http://", "https://", "ftp://"]
    protocols = ["file://"] + remote_protocols


    def info( self ) :
        """
        Returns a string describing the Trait.
        """

        return "an existing local directory or url with a protocol %s" \
               % ", ".join( ["'%s'" % p for p in self.protocols] )


    def _is_remote( self, url ) :
        """
        Returns True if url has a remote_protocol.
        """

        return (True in [url.lower().startswith( p ) \
                         for p in self.remote_protocols])
    
            
    def validate( self, object, name, value ) :
        """
        Validates that the new value is a string which either refers to a remote
        http:// or ftp:// URL, or a local directory which must exist.
        """

        #
        # check for a string
        #
        if( not( isinstance( value, basestring ) ) ) :
            self.error( object, name, value )
            
        newval = value
        
        #
        # if local, value must be a path to an existing directory.
        #
        if( (value != "") and not( self._is_remote( value ) ) ) :
            
            if( value.lower().startswith( "file://" ) ) :
                newval = newval[7:]
                
                if IS_WINDOWS:
                    newval = newval.strip("/")
                

            if( path.exists( newval ) and path.isdir( newval ) ) :
                newval = path.normpath( path.abspath( newval ) )
                newval = "file://%s" % newval

            else :
                self.error( object, name, value )

        return newval



class ExistingFileTrait( TraitHandler ) :
    """
    Trait used for local files which must exist.
    If abspath is True, the validator makes the path to the file an abs path
    if it is not.
    """

    abspath = Bool( False )

    
    def info( self ) :
        """
        Returns a string describing the Trait.
        """

        msg = "a file on disk which must exist"
        return msg


    def validate( self, object, name, value ) :
        """
        Validates that the new value represents an existing file on disk.
        """

        #
        # check for a string
        #
        if( not( isinstance( value, basestring ) ) ) :
            self.error( object, name, value )
        #
        # make abspath if necessary
        #
        if( object.trait( name ).abspath is True ) :
            newval = path.normcase( path.normpath( path.abspath( value ) ) )
        else :
            newval = value

        #
        # value must be a directory which exists
        #
        if( not( path.exists( newval ) ) ) :
            self.error( object, name, value )

        return newval



class ExistingDirectoryTrait( TraitHandler ) :
    """
    Trait used for local directories which must exist.
    If writable is True, the directory must also be writable.
    If abspath is True, the validator makes the dir an abs path if it is not.
    """

    writable = Bool( False )
    abspath = Bool( False )

    
    def info( self ) :
        """
        Returns a string describing the Trait.
        """

        msg = "a directory on disk which must exist"
        if( self.writable ) :
            msg += " and be writable by the current user"
        return msg


    def validate( self, object, name, value ) :
        """
        Validates that the new value represents an existing directory on disk
        and that if self.writable is True, is also writable.
        """

        #
        # check for a string
        #
        if( not( isinstance( value, basestring ) ) ) :
            self.error( object, name, value )
        #
        # make abspath if necessary
        #
        if( object.trait( name ).abspath is True ) :
            newval = path.normcase( path.normpath( path.abspath( value ) ) )
        else :
            newval = value

        #
        # value must be a directory which exists
        #
        if( not( path.exists( newval ) ) or not( path.isdir( newval ) ) ) :
            self.error( object, name, value )

        #
        # check for writeability if necessary
        #
        if( object.trait( name ).writable is True ) :
            tmpname = tempfile.mktemp( dir=newval )
            try :
                open( tmpname, "w" ).close()
            except IOError :
                self.error( object, name, value )
            os.remove( tmpname )

        return newval



class CreatableDirectoryTrait( TraitHandler ) :
    """
    Trait used for local directories which may or may not exist, where if they
    exist they must be writable, and if they dont, the parent directory must
    exist and be writable (in order to eventually create the directory).
    """

    abspath = Bool( False )
    create = Bool( True )

    
    def info( self ) :
        """
        Returns a string describing the Trait.
        """

        return "a directory on disk which is either present and writable or " + \
               "is able to be created (a parent dir exists and is writable)"


    def post_setattr( self, object, name, value ) :
        """
        Called after the new value has been assigned...if create is True,
        create the directory represented by value if it does not exist.
        """

        if( (object.trait( name ).create is True) and
            not( path.exists( value ) ) ) :
            os.makedirs( value )


    def validate( self, object, name, value ) :
        """
        Validates that the new value represents an existing directory on disk
        that is writable, or is able to be created with a call to os.makdirs().
        """

        #
        # check for a string
        #
        if( not( isinstance( value, basestring ) ) ) :
            self.error( object, name, value )
        #
        # Do not accept ""...users must use "." for CWD.
        #
        if( value == "" ) :
            self.error( object, name, value )
        #
        # make abspath if necessary
        #
        if( object.trait( name ).abspath is True ) :
            newval = path.normcase( path.normpath( path.abspath( value ) ) )
        else :
            newval = value
        #
        # find the nearest existing dir
        #
        check_dir = newval
        while( not( path.exists( check_dir ) ) ) :
            prev = check_dir
            check_dir = path.dirname( check_dir )
            #
            # prevent inf. loop
            #
            if( check_dir == prev ) :
                self.error( object, name, value )
        #
        # check for writability
        #
        tmpname = tempfile.mktemp( dir=check_dir )
        try :
            open( tmpname, "w" ).close()
        except IOError :
            self.error( object, name, value )
        os.remove( tmpname )

        return newval


################################################################################
# Instantiate for easy use in Traits-based classes
################################################################################

Url = Trait( "", UrlTrait() )
ExistingFile = Trait( "", ExistingFileTrait() )
ExistingDir = Trait( "", ExistingDirectoryTrait() )
CreatableDir = Trait( "", CreatableDirectoryTrait() )

