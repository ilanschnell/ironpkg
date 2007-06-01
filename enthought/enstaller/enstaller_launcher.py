import time
from optparse import OptionParser
from traceback import extract_tb
import sys
from os import path


from enthought.enstaller.text_io import \
     TextIO
from enthought.enstaller.api import \
     PYVER, ENTHOUGHT_REPO, get_version_string

################################################################################
####  EnstallerLauncher
####
####  Class used to start a standalone Enstaller session.
####
####  The heart of this class is the launch() method which starts a standalone
####  Enstaller session.  If necessary, and permitted by the user, Enstaller is
####  "bootstrapped" (downloaded and installed) prior to starting if it had not
####  been installed before.
################################################################################
class EnstallerLauncher( TextIO ) :
    """
    Class used to start a standalone Enstaller session.
    """
    #
    # The postmortem file...if a crash occurs, send this file to the authors
    #
    postmortem_file = path.abspath( "ENSTALLER_POSTMORTEM.txt" )
    #
    # the Enstaller egg name pattern to match.
    # Note the $ at the end...needed to avoid matching things like foo.egg.info
    #
    enstaller_egg_name = "enstaller-(.*)-py%s.*\.egg$" % PYVER
    #
    # Output messages
    #
    enstaller_import_error = """
The Enstaller package could not be imported...this means Enstaller is not
installed or is broken or missing (need to set PYTHONPATH?)
"""

    install_enstaller_prompt = """
Proceed to download and install Enstaller? (y/n) """

    bootstrapping_enstaller = """
Attempting to download the Enstaller package...
"""

    enstaller_egg_not_found = """
An Enstaller egg for this Python version was not found!
Use the --find-links option to specify a URL which has an Enstaller egg
for Python version %s
""" % PYVER

    unknown_option_msg = """
Enstaller does not appear to be installed and the option "%s"
is not recognized...it is either invalid or requires the complete Enstaller
package to be processed.  The options available at this time are:

"""


    def __init__( self, *args, **kwargs ) :
        """
        Construct with an optional logging_handle (must support file methods
        write() and flush()) used for outputting messages to the user.
        """
        super( EnstallerLauncher, self ).__init__( *args, **kwargs )
        #
        # assign defaults to attributes
        # (overridden when command-line is processed
        #
        self.argv = []
        self.gui = True
        self.install_dir = ""
        self.find_links = []
        self.bootstrap = True
        #
        # setup a file downloader
        #
        self.downloader = Downloader( logging_handle=self.logging_handle,
                                      verbose=self.verbose,
                                      prompting=self.prompting )
        

    def bootstrap_bootstrap( self ) :
        """
        Downloads the latest Enstaller egg to a temp directory to access its
        bootstrap code, where the bootstrap code will then handle the formal
        installation of Enstaller and all necessary dependencies.

        The egg in the temp dir is added to the current sys.path, the bootstrap
        module is imported from it and ran, then the temp egg is "unimported"
        and removed.
        """
        self.log( self.bootstrapping_enstaller )
        #
        # get the URL for the Enstaller egg...this may involve asking the user
        # which version they want.
        #
        url = self.get_enstaller_url()
        #
        # open a temp file to save the egg contents to...it will be installed
        # properly at the end of the bootstrap process
        #
        cache = self.downloader.make_cache()
        egg = self.downloader.download_file( url, cache )
        #
        # import the bootstrap code from the temporary egg and run it
        #
        sys.path.insert( 0, egg )
        from enthought.enstaller.bootstrapper import Bootstrapper
        bs = Bootstrapper( self.find_links, self.gui,
                           logging_handle=self.logging_handle,
                           verbose=self.verbose,
                           prompting=self.prompting )

        try :
            bs.bootstrap( self.install_dir, egg )
        except AssertionError :
            sys.exit( 1 )
        #
        # "unimport" the temporary egg since it may be deleted from disk
        # (assumed to be properly installed at this point)
        #
        sys.path.remove( egg )
        allmods = sys.modules.keys()
        for mod in allmods :
            if( mod.startswith( "enstaller" ) and (mod in sys.modules.keys()) ) :
                del sys.modules[mod]


    @staticmethod
    def build_option_parser( program_name=sys.argv[0],
                             opt_parser_class=OptionParser ) :
        """
        Returns a basic option parser which supports options primarily used for
        bootstrapping Enstaller.  Other Enstaller operations defined in the
        Enstaller egg will add to the option parser returned by this function.
        """
        usage = "USAGE: %prog [options]"
        #
        # Add a new link only if it has not been added before.
        #
        def add_link( option, opt_str, value, parser ) :
            if( len( parser.rargs ) > 0 ) :
                arg = parser.rargs[0]
                if( not( arg.startswith( "-" ) ) ) :
                    if( not( arg in parser.values.find_links ) ) :
                        parser.values.find_links.append( arg )
                    del parser.rargs[0]

        opt_parser = opt_parser_class( prog=program_name, usage=usage,
                                       version=get_version_string() )

        opt_parser.add_option( "-c", "--command-line",
                               dest="gui", default=True,
                               action="store_false",
                               help="do not use/install the Enstaller GUI" )

        opt_parser.add_option( "-d", "--install-dir",
                               dest="install_dir", metavar="<dir>",
                               default="",
                               help="use an alternate directory to install" + \
                               "packages to (defaults to site-packages for" + \
                               "use by all users)" )

        opt_parser.add_option( "-f", "--find-links",
                               dest="find_links", metavar="<repo>",
                               default=[],
                               action="callback", callback=add_link,
                               help="add a package repository URL to the " + \
                               "search list" )

        opt_parser.add_option( "-n", "--no-bootstrap",
                               dest="bootstrap", default=True,
                               action="store_false",
                               help="do not attempt to bootstrap Enstaller" )

        opt_parser.add_option( "-t", "--batch",
                               dest="prompting", default=True,
                               action="store_false",
                               help="batch mode - do not confirm operations" + \
                               "(command-line only)" )

        opt_parser.add_option( "-v", "--verbose",
                               dest="verbose",default=False,
                               action="store_true",
                               help="print debug-level messages" )

        opt_parser.add_option( "--no-default-enthought-repo",
                               dest="use_default_enthought_repo", default=True,
                               action="store_false",
                               help="do not use the Enthought repository " + \
                               "by default" )

        #
        # Override the optparse check_values method in order to add the default
        # Enthought repo last in the order of find_links precedence, if it is to
        # be used at all.
        #
        def check_values( values, args ) :
            find_links = values.find_links
            use_def_en_repo = values.use_default_enthought_repo
            if( use_def_en_repo and not( ENTHOUGHT_REPO in find_links ) ) :
                find_links.append( ENTHOUGHT_REPO )
            return (values, args)
            
        opt_parser.check_values = check_values
        
        return opt_parser


    def get_enstaller_url( self ) :
        """
        Returns a URL to the latest compatible Enstaller egg.
        """
        #
        # add the default repo to any user-specified repos and look for the
        # highest known-compatible Enstaller egg...warn user if not found
        #
        enstaller_url = None
        find_links = self.find_links[:]

        self.debug( "Looking for a known compatible egg...\n" )
        enstaller_url = self.downloader.find_latest_version(
            find_links, self.enstaller_egg_name )
        #
        # if a URL could not be determined, abort
        #
        if( enstaller_url is None ) :
            self.log( self.enstaller_egg_not_found )
            sys.exit( 1 )
            
        return enstaller_url


    def launch( self, argv ) :
        """
        Launches the app, gracefully handling any uncaught exceptions.
        """
        try :
            retcode = self.run( argv )

        except SystemExit, code:
            retcode = code
        
        except Exception, err:
            pm_text = self._write_postmortem()
            self.debug( pm_text )
            retcode = 1

        return retcode


    def run( self, argv, bootstrapping=False ) :
        """
        Runs the "main" function in the Enstaller package used to start a
        standalone session of Enstaller.

        An attempt to import the Enstaller package is made, and if that is
        successful Enstaller is started.  If it could not be imported and the
        user has not disabled bootstrapping, the latest Enstaller egg is
        downloaded and the bootstrap process defined in that egg is run.
        """
        #
        # without processing the args, check for the verbose flag for debugging
        #
        if( ("-v" in argv) or ("--verbose" in argv) ) :
            self.verbose = True

        #
        # If Enstaller is installed, set the version info and pass the command
        # line args to the main function.
        #
        try :
            from enthought.enstaller.main import main
            return main( argv, self.logging_handle )

        #
        # If this point is reached Enstaller is not installed (or is broken).
        # Use the arg processor in this script to examine the command line and
        # determine the next action (bootstrap, print traceback, etc.)
        #
        except ImportError, err :
            #
            # read the command line, continue only if its valid
            #
            args_ok = self._process_command_line( argv )
            if( args_ok != 0 ) :
                return args_ok
            #
            # bootstrap Enstaller--if permitted--by installing the latest
            # Enstaller egg and using its bootstrap module and call run() again.
            #
            if( not( bootstrapping ) ) :
                self.log( self.enstaller_import_error )
                self.log( "\nThe import error was: %s\n" % err )

                if( self.bootstrap ) :
                    if( self.prompt( self.install_enstaller_prompt, True ) ) :
                        self.bootstrap_bootstrap()                    
                        return self.run( argv, bootstrapping=True )
                    else :
                        return 1
            #
            # if this point is reached, there is a bug.
            #
            elif( bootstrapping ) :
                self.log( "\nAn error was encountered while " + \
                          "bootstrapping Enstaller!\n" )

            raise


    def _process_command_line( self, argv ) :
        """
        Read the command line and set attributes on this object.
        """
        logging_handle = self.logging_handle
        unknown_option_msg = self.unknown_option_msg
        #
        # For parsing options for the bootstrap operation, override the error
        # handler to print a message explaining that unknown options may be valid
        # once Enstaller is installed, but not recognized with this opt parser.
        #
        class TempOptParser( OptionParser ) :
            def error( self, msg ) :
                exit_msg = ""
                if( msg.startswith( "no such option: " ) ) :
                    bad_opt = msg.split( ": " )[1]
                    logging_handle.write( unknown_option_msg % bad_opt )
                else :
                    exit_msg = "%s: error: %s\n" % (self.get_prog_name(), msg)

                self.print_help( logging_handle )
                self.exit( 2, exit_msg )

        opt_parser = self.build_option_parser( argv[0], TempOptParser )

        #
        # prevent OptionParser from shutting down the app
        #
        try :
            args_obj = opt_parser.parse_args( args=argv )[0]

        except SystemExit, return_code :
            return return_code

        self.argv = argv
        self.gui = args_obj.gui
        self.install_dir = args_obj.install_dir
        self.find_links = args_obj.find_links
        self.bootstrap = args_obj.bootstrap
        self.prompting = args_obj.prompting
        self.verbose = args_obj.verbose
        #
        # update the downloader with the new options
        #
        self.downloader.prompting = self.prompting
        self.downloader.verbose = self.verbose

        return 0
    

    def _write_postmortem( self ) :
        """
        Formats the last exception in "postmortem text" and writes it to the
        postmortem file for bug reporting.  Returns the pm_text.
        """
        #
        # create the pm text
        #
        (exc, msg, tb) = sys.exc_info()
        self.log( "\nInternal Error: %s: %s\n\n" % (exc, msg) )
        
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
            self.log( "Please submit the following postmortem file to the " + \
                      "authors:\n%s\n\n" % self.postmortem_file )

        except :
            sys.stderr.write( "\nAn internal error occurred and a postmortem " +\
                              "file could not be written!\n" )
            sys.stderr.write( "Here is the postmortem text:\n %s" % pm_text )

        return pm_text
