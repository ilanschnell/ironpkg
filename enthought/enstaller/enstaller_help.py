#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007-03-14
#------------------------------------------------------------------------------

from os import path

from enthought.traits.api import \
     HasTraits, HTML

from enstaller.enstaller_traits import \
     ExistingFile

#
# The default help file.
#
HELP_FILE_PATH = path.join( path.dirname( path.abspath( __file__ ) ),
                            "Enstaller_Help.html" )


class EnstallerHelp( HasTraits ) :
    """
    Class used for presenting help text to users.
    """

    #
    # The html help text.
    #
    html_text = HTML

    #
    # The HTML help file.
    #
    html_file = ExistingFile
    

    #############################################################################
    # Traits handlers, defaults, etc.
    #############################################################################
    
    def _html_file_default( self ) :
        """
        Return the default help file.
        """
        return HELP_FILE_PATH


    def _html_text_default( self ) :
        """
        Returns the contents of self.html_file to be used by default as the html
        help text.
        """
        fh = open( self.html_file )
        text = fh.read()
        fh.close()
        return text

