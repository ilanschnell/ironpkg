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
from pkg_resources import \
     require, DistributionNotFound

from enthought.enstaller.api import \
     ENTHOUGHT_REPO, get_app_version_string, is_standalone_app

from enthought.enstaller.proxy_support import \
     check_and_install_proxy

#
# If True, GUI features will be available.
#
HAVE_GUI = True

#
# Handle the special case of running as part of a "standalone" bundled app egg,
# or as a "traditional" egg requiring additional egg dependencies.
#
if( is_standalone_app ) :

    #
    # Get a distribution object for this egg to get the egg location.
    #
    dists = require( "enstaller" )

    #
    # Get the dist object for the GUI...this will also disable GUI features if
    # any of the GUI packages are not found.
    #
    try :
        dists += require( "enstaller.gui" )
        import wx

    except :
        HAVE_GUI = False

    #
    # Build a list of locations for the enstaller eggs.
    #
    enthought_paths = []    
    for dist in dists :
        e_path = path.join( dist.location, "enthought" )
        if( not( e_path in enthought_paths ) ) :
            enthought_paths.append( e_path )

    #
    # Set the path to enthought to be the standalone enstaller egg(s).  This
    # prevents any other eggs which contribute to the enthought namespace from
    # being found instead of the enthought packages bundled in this egg, which
    # are known to be compatible.
    #
    import enthought
    enthought.__path__ = enthought_paths

    enthought_traits_paths = \
        [path.join( d, "traits" ) for d in enthought_paths]
    import enthought.traits
    enthought.traits.__path__ = enthought_traits_paths

    enthought_traits_ui_paths = \
        [path.join( d, "ui" ) for d in enthought_traits_paths]
    import enthought.traits.ui
    enthought.traits.ui.__path__ = enthought_traits_ui_paths
        
    #
    # Finally, remove any other bundled installs from the path...this only works
    # because these packages are not namespace packages.
    #
    # UPDATE: do not remove these other bundled pacakges for now, since not all
    # platforms are supported and users should be able to use the system
    # wxPython, for example.
    #
    #syspath = sys.path[:]
    #removes = ["wxpython", "numpy", "wininst"]
    #
    #for d in syspath :
    #    matches = [path.basename( d ).lower().startswith( r ) for r in removes]
    #    if( True in matches ) :
    #        sys.path.remove( d )

#
# If not running as a standalone app egg, determine if GUI features should be
# enabled by attempting to import them.
#
elif( HAVE_GUI ) :
    try :
        import wx
        import enthought.enstaller.gui

    except ImportError :
        HAVE_GUI = False

from enthought.enstaller.session import \
     Session
from enthought.enstaller.cli import \
     CLI
from enthought.enstaller.logger import \
     Logger

#
# Normally, ETSConfig.application_home is set properly, but since Enstaller
# may be started by a script that is not in the application dir
# (application_home is based on the dirname of the dir containing the startup  
# script), manually set the application_home here for other modules to use.
#
from enthought.etsconfig.api import ETSConfig
ETSConfig.application_home = path.join(ETSConfig.application_data,
                                       "enstaller")
## from enthought.ets.api import ETS                                        
## ETS.application_home = path.join( ETS.application_data, "enstaller" )


#
# List all of the enstaller options so the easy_install ones can be separated
# out and passed directory to the EasyInstaller class.
#
enstaller_options = [
    "gui",
    "install_dir",
    "find_links",
    "prompting",
    "verbose",
    "use_default_enthought_repo",
    "list_installed",
    "list_repos",
    "remove",
    "upgrade",
    "list_upgrades",
    "activate",
    "deactivate",
    "allow_unstable",
    "allow_hosts",
    "proxy"
]


def build_option_parser( program_name=sys.argv[0] ) :
    """
    Returns an OptionParser instance for use with the Enstaller standalone app.
    """
    usage = "USAGE: %prog [options]"

    #
    # Add a new host pattern only if it has not been added before.
    #
    def add_host_patt( option, opt_str, value, parser ) :
        if( len( parser.rargs ) > 0 ) :
            arg = parser.rargs[0]
            if( not( arg.startswith( "-" ) ) ) :
                if( not( arg in parser.values.allow_hosts ) ) :
                    parser.values.allow_hosts.append( arg )
                del parser.rargs[0]

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

    opt_parser.add_option( "--allow-unstable",
                           dest="allow_unstable", default=False,
                           action="store_true",
                           help="search the enthought \"unstable\" " + \
                           "repository if a package is not found in the " + \
                           "stable one (and all others specified with -f)" )

    opt_parser.add_option("-p", "--proxy",
                          dest="proxy", default='',
                          action="store", type="string",
                          help="use user:password@proxy.location:portnum" \
                              " to use a proxy for accessing the repository" \
                              " where user, password, and portnum are" \
                              " optional")
                          
    #
    # Add other options which are basically passed-through to easy_install
    #
    opt_parser.add_option( "-Z", "--always-unzip",
                           dest="always_unzip", default=False,
                           action="store_true",
                           help="never install as a zipped egg." )

    opt_parser.add_option( "-z", "--zip-ok",
                           dest="zip_ok", default=False,
                           action="store_true",
                           help="always install as a zipped egg." )

    opt_parser.add_option( "-N", "--no-deps",
                           dest="no_deps", default=False,
                           action="store_true",
                           help="do not install dependencies." )

    opt_parser.add_option( "-s", "--script-dir",
                           dest="script_dir", metavar="<dir>",
                           default=None,
                           help="install scripts to <dir>." )

    opt_parser.add_option( "-i", "--index-url",
                           dest="index_url", metavar="<url>",
                           default=None,
                           help="base URL of Python Package Index." )

    opt_parser.add_option( "--record",
                           dest="record", metavar="<file>",
                           default=None,
                           help="filename in which to record list of " + \
                           "installed files." )

    opt_parser.add_option( "-x", "--exclude-scripts",
                           dest="exclude_scripts", default=False,
                           action="store_true",
                           help="do not install scripts." )

    opt_parser.add_option( "-m", "--multi-version",
                           dest="multi_version", default=False,
                           action="store_true",
                           help="make apps require() the package...this " + \
                           "installs the egg \"deactivated\"." )

    opt_parser.add_option( "-b", "--build-directory",
                           dest="build_directory", metavar="<dir>",
                           default=None,
                           help="download/extract/build/ in <dir> and " + \
                           "keep the results." )

##     opt_parser.add_option( "-O", "--optimize",
##                            dest="optimize", metavar="<level>",
##                            default="0",
##                            help="install modules with optimizations " + \
##                            "(.pyo files) in addition to .pyc files.  -O0 " + \
##                            "(the default) means no optimizations, -O is the " + \
##                            "first level (minor optimizations), -O2 is -O " + \
##                            "with all docstrings removed as well." )

    opt_parser.add_option( "-e", "--editable",
                           dest="editable", default=False,
                           action="store_true",
                           help="install specified packages in editable form." )

    opt_parser.add_option( "-H", "--allow-hosts",
                           dest="allow_hosts", metavar="<patterns>",
                           default=[],
                           action="callback", callback=add_host_patt,
                           help="pattern(s) that hostnames must match." )

    #
    # Override the optparse check_values method in order to add the default
    # Enthought repo last in the order of find_links precedence, if it is to
    # be used at all.  If allow-unstable, add the unstable URL after the default.
    #
    def check_values( values, args ) :
        find_links = values.find_links
        use_def_en_repo = values.use_default_enthought_repo
        allow_unstable = values.allow_unstable

        if( use_def_en_repo and not( ENTHOUGHT_REPO in find_links ) ) :
            find_links.append( ENTHOUGHT_REPO )

            unstable_url = "%s/%s" % (ENTHOUGHT_REPO.strip( "/" ), "unstable")
            if( allow_unstable and not( unstable_url in find_links ) ) :
                find_links.append( unstable_url )

        return (values, args)

    opt_parser.check_values = check_values

    return opt_parser


def get_easy_install_options( options_obj ) :
    """
    Returns a dictionary of easy_install options given to enstaller which are to
    be passed through to the EasyInstaller class.
    """
    args = {}

    for arg in dir( options_obj ) :
        argval = getattr( options_obj, arg )
        if( not( arg in ["ensure_value", "read_file", "read_module"] ) and \
            not( arg in enstaller_options ) and \
            not( arg.startswith( "_" ) ) and \
            not( argval is None ) and \
            not( argval is False ) and \
            not( argval == [] ) ) :

            if( argval == "" ) :
                argval = '""'

            args[arg] = argval

    return args


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

    # install a proxy handler if either PROXY_<HOST, PORT, USER, PASS> 
    # environment variables are set or the proxy option is set  
    proxystr = getattr(opt_parser, 'proxy', '')
    try:
        proxy_info = check_and_install_proxy(proxystr)
        if proxy_info['host'] is not None:
            logging_handle.write('Using proxy %s' % proxy_info)
    except:
        logging_handle.write('Error: Bad proxy information: %s' \
                                 % proxystr)
        return 2
    
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
                           find_links     = options.find_links,
                           allow_hosts    = options.allow_hosts )

        #
        # Scan sys.path...this is needed for all actions.
        #
        session.initialize()

        #
        # Set the install dir here if specified on the command line so its not
        # overridden by any preference file settings.
        #
        if( options.install_dir != "" ) :
            session.install_dir = options.install_dir

        #
        # Add all other options specified on the command-line to the session.
        #
        session.extra_easy_install_args = get_easy_install_options( options )

        #
        # Launch either the GUI or the CLI with the appropriate action.
        #
        if( options.gui ) :
            gui = GUI( logging_handle=logger,
                       verbose=options.verbose,
                       session=session )
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
                retcode = cli.upgrade( package_specs )

            elif( options.list_upgrades ) :
                retcode = cli.list_upgrades( package_specs )

            elif( options.activate ) :
                retcode = cli.activate( package_specs )

            elif( options.deactivate ) :
                retcode = cli.deactivate( package_specs )

            else :
                retcode = cli.install( package_specs )

    return retcode


if( __name__ == "__main__" ) :
    sys.exit( main( sys.argv ) )

