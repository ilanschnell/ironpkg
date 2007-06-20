#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007-03-10
#------------------------------------------------------------------------------

import sys
from os import path

from enthought.traits.api import \
     HasTraits, Instance, Constant, List, Str, Dict
from enthought.app_data_locator.api import \
     AppDataLocator

from enthought.enstaller.text_io import \
     TextIO
from enthought.enstaller.url_util import \
     URLUtil
from enthought.enstaller.enstaller_traits import \
     CreatableDir, Url


class EULAManager( HasTraits, TextIO ) :
    """
    Class used for presenting End-User License Agreements to users.
    """

    #
    # Variables used for defining the state file for EULAs that Enstaller
    # has encountered before.
    # (for some reason, this trait cannot be a File...if it is, a windowing
    # display must be available even if using the CLI.
    #
    #eula_state_file = File
    eula_state_file = Str
    _eula_state_filename = Constant( "eulas" )
    _eula_state_dir = CreatableDir( abspath=True, create=True )

    #
    # The list of URLs which are to be checked for EULAs
    #
    urls = List( Url )

    #
    # The name of the EULA file to download
    #
    eula_file_name = Constant( "EULA.txt" )

    #
    # The dictionary mapping the URLs to their EULAs that the user has previously
    # agreed to.  These are stored in the self.eula_state_file
    #
    accepted_eulas = Dict( Str, Str )

    #
    # The dictionary mapping the URLs to their EULAs that are currently published
    # at the URL.  These are downloaded each time self.urls changes.
    #
    downloaded_eulas = Dict( Url, Str )

    #
    # Instance of a URLUtil used for accessing URLs with error handling.
    #
    _urlutil = Instance( URLUtil )
    

    def __init__( self, **kwargs ) :
        """
        Required to be called with non-Traits TextIO args and have them set
        properly.  Also sets TextIO attrs with defaults.
        """
        
        self.verbose = kwargs.pop( "verbose", False )
        self.prompting = kwargs.pop( "prompting", True )
        self.logging_handle = kwargs.pop( "logging_handle", sys.stdout )

        super( EULAManager, self ).__init__( **kwargs )


    def agree_to_url_eulas( self, urls ) :
        """
        Accepts a list of URLs (assumed to be URLs in the self.downloaded_eulas
        keys) and adds them and their EULA text to the self.accepted_eulas dict,
        then writes the self.accepted_eulas dict to the state file.
        """

        #
        # Accept a string representing a single URL as well.
        #
        if( isinstance( urls, basestring ) ) :
            urls = [urls]

        #
        # Update the accepted EULAs with the new EULAs from the URLs passed in.
        #
        for url in urls :
            self.accepted_eulas[url] = self.downloaded_eulas[url]

        #
        # Write all accepted EULAs to the state file.
        #
        self._write_state_file()


    def disagree_to_url_eulas( self, urls ) :
        """
        Accepts a list of URLs (assumed to be URLs in the self.accepted_eulas
        keys) and removes them and their EULA text from the self.accepted_eulas
        dict, then writes the self.accepted_eulas dict to the state file.
        """

        #
        # Accept a string representing a single URL as well.
        #
        if( isinstance( urls, basestring ) ) :
            urls = [urls]

        #
        # Remove the URLs and their EULAs from the accepted EULAs dict.
        #
        for url in urls :
            self.accepted_eulas.pop( url, None )

        #
        # Write all accepted EULAs to the state file.
        #
        self._write_state_file()

        
    def get_new_eulas( self ) :
        """
        Returns a dictionary of URL to EULA text for each EULA that has not been
        agreed to in the past (as determined by the state file).  A EULA is
        considered new if it has never been seen before or if it has changed
        since last agreed to.
        """

        #
        # Start by re-reading all EULAs since they may have changed since this
        # method was last called.
        #
        self._read_all_url_eulas()
        
        new_eulas = {}
        accepted_urls = self.accepted_eulas.keys()

        #
        # Check each of the current EULAs to see if they are in the accepted
        # dictionary.
        #
        for (url, eula) in self.downloaded_eulas.items() :
            #
            # If present in accepted and the text is the same, continue.
            #
            if( url in accepted_urls ) :
                if( eula == self.accepted_eulas[url] ) :
                    continue
            #
            # Otherwise, add it to the new_eulas to return.
            #
            new_eulas[url] = eula

        return new_eulas


    #############################################################################
    # Protected interface.
    #############################################################################

    def _read_all_url_eulas( self ) :
        """
        (Re)creates the downloaded_eulas dict.
        """

        self.downloaded_eulas = {}
        
        for url in self.urls :
            self._read_url_eula( url )


    def _read_url_eula( self, url ) :
        """
        Downloads and stores the EULA for the URL in the downloaded_eulas dict.
        If the URL does not have a EULA, downloaded_eulas is unchanged.
        """

        eula = None
        eula_text = ""
        #
        # Set the URLUtil to raise exceptions instead of logging URLs which are
        # not present (many sites do not have EULAs)
        #
        old_reraise = self._urlutil.reraise_on_bad_urls
        self._urlutil.reraise_on_bad_urls = True

        #
        # Try to open the EULA...if an exception was raised then the site 
        # probably does not have one.
        #
        try :
            eula = self._urlutil.urlopen( "%s/%s" % (url.rstrip( "/" ),
                                                     self.eula_file_name) )
        except IOError :
            eula = None

        #
        # Reset the URLUtil instance to log exceptions (or whatever the
        # original setting was).
        #
        self._urlutil.reraise_on_bad_urls = old_reraise

        #
        # If a EULA was retrieved, read it.
        #
        if( not( eula is None ) ) :
            txt = eula.read().strip()
            #
            # Try to handle Apache server responses that do not raise an
            # IOError but do not return a EULA either because there isn''t one
            # as well other responses which return not found messages.
            #
            if( not( "<h1>Not Found</h1>" in txt ) and \
                (txt != "Not Found") ) :
                eula_text = txt

        #
        # Finally, if actual EULA text was read, save it, otherwise log message.
        #
        if( eula_text != "" ) :
            #
            #  If the URL was accepted before but the text changed, remove it
            # from the accepted dict.
            #
            if( (url in self.accepted_eulas.keys()) and
                (self.accepted_eulas[url] != eula_text) ) :
                self.accepted_eulas.pop( url )
                
            self.downloaded_eulas[url] = eula_text
        else :
            self.debug( "No %s file found for %s.\n" % (self.eula_file_name,
                                                        url) )


    def _write_state_file( self ) :
        """
        Write all accepted EULAs to the state file.
        """
        
        state_file = open( self.eula_state_file, "w" )
        state_file.write( "accepted_eulas = %s" % self.accepted_eulas )
        state_file.close()


    #############################################################################
    # Traits handlers, defaults, etc.
    #############################################################################
    
    def _accepted_eulas_default( self ) :
        """
        Returns the default value of the accepted_eulas dict, which is the dict
        stored in the eula state file, or {} if it does not exist.
        """

        locals = {}
        execfile( self.eula_state_file, {}, locals )
        return locals.get( "accepted_eulas", {} )


    def _eula_state_file_default( self ) :
        """
        Returns the path to the EULA state file.

        Creates the file and the containing directories if necessary.
        """

        #
        # Assign the default value of _eula_state_dir here, since a _default
        # method for this does not fire the post_setattr method for the trait,
        # which is required for properly creating the dir if it does not exist.
        #
        self._eula_state_dir = AppDataLocator.application_home
        
        eula_state_file = path.join( self._eula_state_dir,
                                     self._eula_state_filename )

        #
        # If the EULA state file does not exist, create an empty one.
        #
        if( not( path.exists( eula_state_file ) ) ) :
            open( eula_state_file, "w" ).close()

        return eula_state_file

        
    def _urls_changed( self, old, new ) :
        """
        (Re)creates the downloaded_eulas dict when the url list is changed.
        """

        self._read_all_url_eulas()
        

    def _urls_items_changed( self, event ) :
        """
        Updates the downloaded_eulas dict when items are added or removed from
        the url list.
        """

        #
        # Read each additional URL that was added to the list.
        #
        if( len( event.added ) > 0 ) :
            for url in event.added :
                self._read_url_eula( url )
        #
        # Remove the EULA for each URL that has been removed.
        #
        if( len( event.removed ) > 0 ) :
            for url in event.removed :
                self.downloaded_eulas.pop( url, None )

        
    def __urlutil_default( self ) :
        """
        Return a default instance of a URLUtil to use.
        """

        return URLUtil( logging_handle=self.logging_handle,
                        verbose=self.verbose,
                        prompting=self.prompting )

