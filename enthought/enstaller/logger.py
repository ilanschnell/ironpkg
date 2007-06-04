#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007-02-22
#------------------------------------------------------------------------------

from enthought.traits.api import \
     HasTraits, List, Str, Int, Bool

#
# Try to import wx so that if a GUI is used it can be updated appropriately
# otherwise set to None so code can check if wx is available.
#
try :
    import wx
except ImportError :
    wx = None



class Logger( HasTraits ) :
    """
    Logs messages to the list of targets, all of which are assumed to have
    write() and flush() methods.
    Can also keep a fixed-sized buffer of previous log messages.

    """
    #
    # The list of file handles to write to
    #
    targets = List

    #
    # If copy_to_buffer is False the buffer and all bookkeeping vars are not used
    #
    copy_to_buffer = Bool( True )

    #
    # The buffer contains *roughly* buffer_size strings.  As many as overflow
    # additional strings can be added before the buffer is trimmed back down to
    # buffer_size by removing the oldest entries.
    #
    buffer = Str
    buffer_size = Int( 1000 )
    overflow = Int( 100 )
    linecount = Int


    def flush( self ) :
        """
        Flush all file handles.

        """
        for target in self.targets :
            target.flush()


    def write( self, msg ) :
        """
        Writes to all file handles and the buffer if set.

        """
        #
        # Write the message to all targets first
        #
        self._write_to_targets( msg )

        #
        # Update the buffer if necessary.
        #
        if( self.copy_to_buffer ) :
            self.linecount += msg.count( "\n" )
            self.buffer += msg

            #
            # Do cleanup if the lines have exceeded the overflow limit
            #
            if( self.linecount > (self.buffer_size + self.overflow) ) :
                num_lines_to_remove = self.linecount - self.buffer_size

                line_ends_found = 0
                i = 0
                while( line_ends_found < num_lines_to_remove ) :
                    if( self.buffer[i] == "\n" ) :
                        line_ends_found += 1
                    i += 1
                self.buffer = self.buffer[i:]
                self.linecount = self.buffer_size

            #
            # If wx is available, yield so the GUI thread can update.
            #
            if( not( wx is None ) ) :
                wx.Yield()


    #############################################################################
    # Protected interface.
    #############################################################################

    def _write_to_targets( self, msg ) :
        """
        Writes to all file handles.
        """
        for target in self.targets :
            target.write( "%s" % msg )


