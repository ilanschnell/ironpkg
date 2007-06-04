#------------------------------------------------------------------------------
# Copyright (c) 2007, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Rick Ratzel - 2006-06-27
#------------------------------------------------------------------------------

import sys
import optparse
import site
import os
from os import path

from enthought.enstaller.downloader import \
     Downloader
from enthought.enstaller.api import \
     ENTHOUGHT_REPO, get_app_version_string
from enthought.enstaller.session import \
     Session
from enthought.enstaller.cli import \
     CLI
from enthought.enstaller.logger import \
     Logger

#
# Set a flag indicating if the Enstaller GUI was installed.
#
try :
    import enthought.enstaller.gui
    HAVE_GUI = True
except ImportError :
    HAVE_GUI = False

#
# Normally, ETS.application_home is set properly, but since Enstaller may be
# started by a script that is not in the application dir (application_home is
# based on the dirname of the dir containing the startup script), manually set
# the application_home here for other modules to use.
#
from enthought.ets.api import \
     ETS
ETS.application_home = path.join( ETS.application_data, "enstaller" )


def build_option_parser( program_name=sys.argv[0] ) :
    """
    Returns an OptionParser instance for use with the Enstaller standalone app.
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

    #
    # Define a callback function for the opt_parser which makes sure only one
    # action at a time is performed and that a package name was given if needed.
    #
    all_actions = ["list_installed", "list_repos", "remove", "upgrade",
                   "list_upgrades", "activate", "deactivate"]
    need_package_actions = ["--remove", "--activate", "--deactivate"]
    
    def check_valid_action( option, opt_str, value, parser ) :
        setattr( parser.values, option.dest, True )
        actions = [getattr( parser.values, a ) for a in all_actions]
        #
        # Check that only one action was given
        #
        if( actions.count( True ) > 1 ) :
            msg = "Cannot combine Enstaller actions. Please specify only one of:"
            msg += " %s" % ", ".join( ['"--%s"' % a for a in all_actions] )
            raise optparse.OptionValueError( msg )
        #
        # Check if at least one package was given, if needed
        #
        if( option.get_opt_string() in need_package_actions ) :
            found_package_spec = False
            for arg in (parser.largs + parser.rargs) :
                if( not( arg.startswith( "-" ) ) ) :
                    found_package_spec = True
                    break
            if( not( found_package_spec ) ) :
                msg = "Must specify at least one package with the: " + \
                      "%s action" % opt_str
                raise optparse.OptionValueError( msg )

    #
    # Create an OptionParser and initialize with Enstaller options.
    #
    opt_parser = optparse.OptionParser( prog=program_name, usage=usage,
                                        version=get_app_version_string() )

    opt_parser.add_option( "-c", "--command-line",
                           dest="gui", default=True,
                           action="store_false",
                           help="do not use the Enstaller GUI" )

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

    opt_parser.add_option( "-t", "--batch",
                           dest="prompting", default=True,
                           action="store_false",
                           help="batch mode - do not confirm operations " + \
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

    opt_parser.add_option( "-l", "--list-installed",
                           dest="list_installed", default=False,
                           action="callback", callback=check_valid_action,
                           help="print information about a package or " + \
                           "packages installed (default is all packages)" )

    opt_parser.add_option( "-L", "--list-repos",
                           dest="list_repos", default=False,
                           action="callback", callback=check_valid_action,
                           help="print information about a package or " + \
                           "packages available from the repositries " + \
                           "(default is all available packages)" )

    opt_parser.add_option( "-r", "--remove",
                           dest="remove", default=False,
                           action="callback", callback=check_valid_action,
                           help="remove a package or packages installed" )

    opt_parser.add_option( "-U", "--upgrade",
                           dest="upgrade", default=False,
                           action="callback", callback=check_valid_action,
                           help="upgrade a package or packages installed " + \
                           "(default is all packages)" )

    opt_parser.add_option( "-u", "--list-upgrades",
                           dest="list_upgrades", default=False,
                           action="callback", callback=check_valid_action,
                           help="list the upgrades available to a package " + \
                           "or packages installed (default is all packages)" )

    opt_parser.add_option( "-A", "--activate",
                           dest="activate", default=False,
                           action="callback", callback=check_valid_action,
                           help="activate a package or packages installed" )

    opt_parser.add_option( "-D", "--deactivate",
                           dest="deactivate", default=False,
                           action="callback", callback=check_valid_action,
                           help="deactivate a package or packages installed" )

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


def override_opt_parse_output( opt_parser, logging_handle ) :
    """
    Replaces the methods on the opt_parser that write to stdout/stderr with ones
    that write to the logging_handle instead.
    This should not be called on opt_parser instances which have custom error()
    or print_usage() methods!
    """

    def error( msg ) :
        opt_parser.print_usage( logging_handle )
        opt_parser.exit( 2, "%s: error: %s\n" \
                         % (opt_parser.get_prog_name(), msg) )

    def print_usage( file=None ) :
        if( opt_parser.usage ) :
            print >>logging_handle, opt_parser.get_usage()

    def print_help( file=None ) :
        logging_handle.write( opt_parser.format_help() )

    def exit( status=0, msg=None ) :
        if( msg ) :
            logging_handle.write( msg )
        sys.exit( status )

    def print_version( file=None ) :
        if( opt_parser.version ) :
            print >>logging_handle, opt_parser.get_version()

    opt_parser.error = error
    opt_parser.print_usage = print_usage
    opt_parser.print_help = print_help
    opt_parser.exit = exit
    opt_parser.print_version = print_version


def postprocess_args( opt_parser, options, package_specs, logging_handle ) :
    """
    Checks the complete set of args and checks that they make sense for this
    particular application.  Also removes the program name from the list of
    package_specs
    """

    retcode = 0

    #
    # Sometimes, missing args to -d will cause it to treat the next option
    # as the install directory...bug in optparse?
    #
    if( options.install_dir.startswith( "-" ) ) :
        logging_handle.write( "Error: Bad install directory: %s\n" \
                              % options.install_dir )
        retcode = 2

    cli_options_given = (len( package_specs ) > 0) or options.list_installed or \
                        options.list_repos or options.remove or \
                        options.upgrade or options.list_upgrades or \
                        options.activate or options.deactivate

    cli_mode = not( HAVE_GUI ) or cli_options_given

    #
    # override the GUI default if cli args were given.
    #
    if( cli_mode ) :
        options.gui = False
    #
    # The --install-dir option can only be given with the install action
    #
    if( (options.install_dir != "") and
        (options.list_installed or options.list_repos or options.remove or \
         options.activate or options.deactivate) ) :
        logging_handle.write( "Error: The --install-dir (-d) option can " + \
                              "only be used when installing or upgrading " + \
                              "packages.\n" )
        retcode = 2
    #
    # Make sure there is something to do if a GUI is not to be started.
    #
    elif( not( options.gui ) and not( cli_mode ) ) :
        logging_handle.write( "Error: Must provide one or more packages " + \
                              "to install or an action to perform when " + \
                              "not using the Enstaller GUI.\n" )
        retcode = 2
    #
    # Issue a warning if no prompting selected with GUI.
    #
    elif( options.gui and not( options.prompting ) ) :
        logging_handle.write( "Warning: --batch (-t) is ignored when using " + \
                              "the Enstaller GUI.\n" )

    #
    # If the GUI is not installed and no options were given, print help
    #
    elif( not( HAVE_GUI ) and not( cli_options_given ) ) :
        opt_parser.print_help()
        sys.exit( 0 )
        
    return retcode



def main( argv=sys.argv, logging_handle=sys.stdout ) :
    """
    Starts a new Session, initializing it based on the command-line args passed
    in and logging all output to logging_handle.  This function should not raise
    any exceptions...instead it will return non-0 on error and log a message to
    the logging handle.
    """

    assert (len( argv ) > 0), "argv arg to main cannot be an empty list"
    retcode = 1
    #
    # Build a command-line processor that uses the logging_handle for output.
    #
    opt_parser = build_option_parser( argv[0] )
    
    #
    # Catch sys.exit to prevent OptionParser from shutting down the app if the
    # args were invalid.
    #
    try :
        (options, package_specs) = opt_parser.parse_args( argv[1:] )
        retcode = postprocess_args( opt_parser, options, package_specs,
                                    logging_handle )
    
    except SystemExit, exit_code :
        retcode = exit_code

    #
    # If the args were valid, instantiate a session and call methods based on
    # args passed in
    #
    if( retcode == 0 ) :
        #
        # Import here before a session is instantiated but after the module is
        # completely imported so only the GUI option imports GUI dependencies.
        #
        if( options.gui ) :
            from enthought.enstaller.gui.gui import GUI
        #
        # Instantiate a session and a logger, used for both GUI and CLI
        #
        logger = Logger( targets=[logging_handle] )
        session = Session( logging_handle = logger,
                           verbose        = options.verbose,
                           prompting      = options.prompting,
                           find_links     = options.find_links )
        #
        # Scan sys.path...this is needed for all actions.
        #
        session.initialize()
        install_dir = (options.install_dir or Downloader.get_site_packages_dir())
        
        #
        # Launch either the GUI or the CLI with the appropriate action.
        #
        if( options.gui ) :
            gui = GUI( logging_handle=logger,
                       verbose=options.verbose,
                       session=session )
            gui.install_dir = install_dir
            retcode = gui.show()

        else :
            logger.copy_to_buffer = False
            cli = CLI( logging_handle=logger,
                       verbose=options.verbose,
                       prompting=options.prompting,
                       session=session )

            if( options.list_installed ) :
                retcode = cli.list_installed( package_specs )

            elif( options.list_repos ) :
                retcode = cli.list_repos( package_specs )

            elif( options.remove ) :
                retcode = cli.remove( package_specs )

            elif( options.upgrade ) :
                retcode = cli.upgrade( install_dir, package_specs )

            elif( options.list_upgrades ) :
                retcode = cli.list_upgrades( install_dir, package_specs )

            elif( options.activate ) :
                retcode = cli.activate( package_specs )

            elif( options.deactivate ) :
                retcode = cli.deactivate( package_specs )

            else :
                retcode = cli.install( install_dir, package_specs )


    return retcode


if( __name__ == "__main__" ) :
    sys.exit( main( sys.argv ) )
