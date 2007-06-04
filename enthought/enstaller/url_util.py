#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007-05-27
#------------------------------------------------------------------------------

import re
import urllib

from enthought.enstaller.text_io import \
     TextIO


class URLUtil( TextIO ) :
    """
    Class to gracefully handle timeouts, etc. for urllib functions.
    """

    retries_on_timeout = 2

    retry_msg = "Timed out accessing %s...retrying.\n"
    
    bad_url_warning = "Warning: URL %s could not be opened.\n" + \
                      "The error was: %s\n" + \
                      "This URL will not be used.\n"

    too_many_retries = "Operation timed out %s times while trying to " + \
                       "access URL %s.\nThis URL will not be used.\n"
    
    successful_read_msg = "Successfully read %s\n"

    #
    # Set to True if the wrapper is to re-raise bad URL exceptions instead of
    # logging them (will still retry on timeouts)
    #
    reraise_on_bad_urls = False
    
    
    def urlopen( self, url ) :
        """
        Calls urllib.urlopen() on the URL, handling bad URLs and timeouts.
        """
        #
        # urllib.urlopen does not accept file:// (???)
        #
        if( re.match( "^file://", url, re.IGNORECASE ) ) :
            url = url[7:]
            
        return self._urllib_wrapper( urllib.urlopen, url )


    def urlretrieve( self, url, dest=None, reporthook=None ) :
        """
        Calls urllib.urlretrieve() on the URL, handling bad URLs and timeouts.
        """
        return self._urllib_wrapper( urllib.urlretrieve, url, dest, reporthook )
    

    def _urllib_wrapper( self, func, url, *args ) :
        """
        Calls urllib functions which take a url as the first arg, handling
        errors gracefully and retries on timeouts.
        """
        retval = None
        retries = 0
        err = ""
        
        while( retries < self.retries_on_timeout ) :
            try :
                retval = apply( func, ((url, ) + args) )
                #
                # Print a confirmation if the URL had to be retried.
                #
                if( retries > 0 ) :
                    self.log( self.successful_read_msg % url )
                break
            
            except IOError, err :
                #
                # Check for timeout, all other socket errs are bad URLs
                #
                socket_err = ""
                if( err.args[0] == "socket error" ) :
                    socket_err = err.args[1].args[1]

                if( socket_err == "Operation timed out" ) :
                    self.log( self.retry_msg % url )
                    retries += 1
                    continue

                if( self.reraise_on_bad_urls ) :
                    raise
                else :
                    self.log( self.bad_url_warning % (url, err) )
                    break
        #
        # Print a message if the max retries has been exceeded.
        #
        if( retries >= self.retries_on_timeout ) :
            self.log( self.too_many_retries % (url, self.retries_on_timeout+1) )
            
        return retval
