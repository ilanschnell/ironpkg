#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2007-06-03
#------------------------------------------------------------------------------

import time
from traceback import extract_tb
import sys
from os import path



class Launcher :
    """
    Class used to start a standalone Enstaller application.
    """

    #
    # The output handle which error messages are to be written to.
    #
    err_handle = sys.stderr

    #
    # The postmortem file...if a crash occurs, send this file to the authors.
    #
    postmortem_file = path.abspath( "ENSTALLER_POSTMORTEM.txt" )

    #
    # Error messages.
    #
    enstaller_import_error = """
The Enstaller package could not be imported...this means Enstaller is not
installed or is broken or missing.
"""


    def __init__( self, argv=sys.argv ) :
        """
        Initialize with the command-line args to be passed to the Enstaller
        "main" function.
        """
        self.argv = argv

        #
        # Look for the verbose flag and use it to determine if any tracebacks
        # will be printed to the err_handle, or just to the postmortem file.
        #
        if( ("-v" in argv) or ("--verbose" in argv) ) :
            self.debug = True
        else :
            self.debug = False


    def launch( self ) :
        """
        Launches the app''s "main", gracefully handling any uncaught exceptions.
        """
        retcode = 1

        #
        # Import the app here...handle this separately since ImportErrors
        # *usually* represent a packaging problem.
        #
        try :
            from enthought.enstaller.main import main

        except ImportError, err :
            self.err_handle.write( self.enstaller_import_error )

            pm_text = self._write_postmortem()
            if( self.debug ) :
                self.err_handle.write( pm_text )
            retcode = 1

        else :
            #
            # Run the Enstaller main, catch all uncaught exceptions.
            #
            try :
                retcode = main( self.argv )

            except SystemExit, code:
                retcode = code

            except Exception, err:
                pm_text = self._write_postmortem()
                if( self.debug ) :
                    self.err_handle.write( pm_text )
                retcode = 1

        return retcode
    

    def _write_postmortem( self ) :
        """
        Formats the last exception in "postmortem text" and writes it to the
        postmortem file for bug reporting.  Returns the pm_text.
        """
        #
        # create the pm text
        #
        (exc, msg, tb) = sys.exc_info()
        self.err_handle.write( "\nInternal Error: %s: %s\n\n" % (exc, msg) )
        
        pm_text = "Error: %s\n" % msg
            
        for (filename, lineno, funcname, text) in extract_tb( tb ) :
            pm_text += "  File %s, line %s, in %s\n" \
                       % (filename, lineno, funcname)
            pm_text += "     %s\n" % text
        pm_text += "\n"
        #
        # Extra info for the file
        #
        header = "*" * 79 + "\n"
        header += "* Time of death: %s\n" % time.asctime()
        header += "* Command line: %s\n" % sys.argv
        header += "* Python executable: %s\n" % sys.executable
        header += "* Python version: %s\n" % sys.version
        header += "*" * 79 + "\n"
        #
        # write the file
        #
        try :
            pm_file = open( self.postmortem_file, "a" )
            pm_file.write( header + pm_text )
            pm_file.close()

            self.err_handle.write( "Please submit the following postmortem " + \
                                   "file to the authors:\n%s\n\n" \
                                   % self.postmortem_file )

        except :
            self.err_handle.write( "\nAn internal error occurred and a " +\
                                   "postmortem file could not be written!\n" )
            self.err_handle.write( "Here is the postmortem text:\n %s" \
                                   % pm_text )

        return pm_text



def launch() :
    """
    Function which provides a console_script entry point for the Enstaller app.
    """
    sys.exit( Launcher( sys.argv ).launch() )


#
# Allow running this module as a script
#
if( __name__ == "__main__" ) :
    launch()


