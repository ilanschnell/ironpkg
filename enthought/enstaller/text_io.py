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

import sys
import types


class TextIO( object ) :
    """
    A mixin which provides methods for logging output messages and reading user
    input.  The methods assume a logging_handle has been set (usually
    sys.stdout) has standard file object methods.
    """

    def __init__( self, logging_handle=sys.stdout,
                  verbose=False, prompting=True ) :
        #
        # the logging_handle must be an object with at least a write
        # and flush method
        #
        self.logging_handle = logging_handle
        self.verbose = verbose
        self.prompting = prompting


    def debug( self, msg ) :
        """
        Log msg if self.verbose == True.
        """
        if( self.verbose ) :
            self.log( msg )


    def log( self, msg ) :
        """
        Writes msg to the logging handle, if set.
        """
        if( not( self.logging_handle is None ) ) :
            self.logging_handle.write( msg )


    def prompt( self, prompt_text, default_response ) :
        """
        Prints the prompt_text and reads stdin if the prompt_flag is True.  If
        the flag is False, returns the default_response.  If the
        default_response is a bool, the input read is y/n, yes/no, etc. and is
        converted to a bool...if default_response is a string, response is
        converted to a string, etc.
        """
        response = None
        expected_type = type( default_response )
        
        if( self.prompting ) :
            while( response is None ) :
                raw_response = self.prompter( prompt_text ).strip()
                #
                # boolean
                #
                if( expected_type == types.BooleanType ) :
                    if( raw_response.lower() in ["y", "yes"] ) :
                        response = True
                    elif( raw_response.lower() in ["n", "no"] ) :
                        response = False
                #
                # number
                #
                elif( expected_type == types.IntType ) :
                    if( raw_response.isdigit() ) :
                        response = int( raw_response )
                #
                # string
                #
                else :
                    response = raw_response
        else :
            response = default_response

        return response


    def prompter( self, msg ) :
        """
        Prints message and returns user input...meant to be overridden if the
        launcher is not used from a console.
        """
        self.log( msg )
        return raw_input()
