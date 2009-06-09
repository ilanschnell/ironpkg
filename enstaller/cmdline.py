#------------------------------------------------------------------------------
# Copyright (c) 2008-2009 by Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#------------------------------------------------------------------------------

import datetime
import os
import sys
import time
from distutils import sysconfig

from enstaller.config import get_configured_index, get_configured_repos
from enstaller.proxy.api import setup_proxy
from enstaller.repository import HTMLRepository, RepositoryUnion
from enstaller.requirements import (deactivate_requirement, get_local_repos,
                                    get_site_packages, install_requirement,
                                    remove_requirement)
from enstaller.rollback import (parse_project_str, retrieve_states,
                                rollback_state, save_state)
from enstaller.upgrade import get_upgrade_str
from enstaller.utilities import rst_table, query_user, user_select
from logging import (basicConfig, error, warning, info, debug, DEBUG, INFO,
                     WARNING, ERROR)
from optparse import OptionParser
from pkg_resources import Requirement


try:
    from enstaller import __version__
except ImportError:
    from __init__ import __version__



def upgrade_project(keys, local_repos=None, remote_repos=None,
    interactive=True, dry_run=False, term_width=0, verbose=False):
    """ Upgrade a project, if possible.
    """
    # Before we do anything, save the current working state of the
    # environment to a rollback point.
    # TODO:  If the upgrade fails, we need to rollback to this save point.
    save_state(verbose=verbose)

    if local_repos == None:
        local_repos = get_local_repos()
    local = RepositoryUnion(get_local_repos())
    requirements = []

    # If no explicit project(s) were specified to upgrade, try to upgrade
    # all of the local projects installed.
    if len(keys) == 0:
        for project in local.projects:
            pkg = local.projects[project].active_package
            if pkg:
                keys.append(project)

    for key in keys:
        # All of the keys in the local.projects dictionary are lowercase, so
        # convert all of the user-specified keys to lowercase.
        key = key.lower()

        # If the user specified a project which isn't installed, just skip it.
        try:
            active_local_projects = [project
                for project in local.projects[key].projects
                    if project.active]
        except KeyError:
            print("Skipping %s because it is not installed on your system." %
                  key)
            continue

        if active_local_projects:
            pkg = active_local_projects[0].active_package

            # Retrieve an upgrade string based on the package name/version.
            req_str = get_upgrade_str(key, pkg.version)

            # Create a requirement object from our requirement string.
            requirement = Requirement.parse(req_str)
        else:
            max_pkg = None
            for pkg in local.projects[key].packages:
                if max_pkg is None or pkg > max_pkg:
                    max_pkg = pkg
            if max_pkg is not None:
                req_str = get_upgrade_str(key, max_pkg.version)
                requirement = Requirement.parse(req_str)
            else:
                requirement = Requirement.parse(project)
        requirements.append(requirement)

    # Try to install all of the generated requirements.
    install_requirement(requirements, local_repos=local_repos,
        remote_repos=remote_repos, interactive=interactive, dry_run=dry_run,
        term_width=term_width)

    # After we have finished the upgrade, we save the new state.
    # TODO:  If the upgrade failed, we should instead revert to the
    #        previous state.
    save_state(verbose=verbose)


def update_project(projects, local_repos=None, remote_repos=None,
    interactive=True, dry_run=False, term_width=0, verbose=False):
    """\
    Update a project, if possible.

    """
    # Before we do anything, save the current working state of the environment
    # to a rollback point.
    # TODO:  If the upgrade fails, we need to rollback to this save point.
    save_state(verbose=verbose)

    # Ensure we know what our local repository consists of.
    if local_repos == None:
        local_repos = get_local_repos()
    local = RepositoryUnion(local_repos)

    # If no explicit project(s) were specified to update, add all locally
    # installed projects to those we'll try to update.
    if len(projects) == 0:
        for project in sorted(local.projects):
            pkg = local.projects[project].active_package
            if pkg:
                projects.append(project)

    # Otherwise, since all of the name in the local.projects dictionary
    # are lowercase, we might as well make them all that way for consistency
    # sake.
    else:
        projects = [name.lower() for name in projects]

    # Determine the requirement specification needed for each project.
    requirements = []
    for name in projects:

        # If the user specified a project which isn't installed, just skip it.
        try:
            active_local_projects = [project
                for project in local.projects[name].projects
                if project.active]
        except KeyError:
            if verbose:
                print ("Skipping %s because it is not installed on your "
                    "system.") % name
            continue

        # If we have a current version active, then we use it's version to
        # to determine what a valid update would be.
        if active_local_projects:
            pkg = active_local_projects[0].active_package
            req_str = get_upgrade_str(name, pkg.version, upgrade=False)
            requirement = Requirement.parse(req_str)

        # Otherwise, we try to build an upgrade requirement from the largest
        # version number of all inactive versions.
        else:
            max_pkg = None
            for pkg in local.projects[name].packages:
                if max_pkg is None or pkg > max_pkg:
                    max_pkg = pkg
            if max_pkg is not None:
                req_str = get_upgrade_str(name, max_pkg.version, upgrade=False)
                requirement = Requirement.parse(req_str)
            else:
                requirement = Requirement.parse(project)
        requirements.append(requirement)
    if not requirements:
        return
    if verbose:
        print 'Generated requirements for updates:'
        for r in requirements:
            print '\t%s' % r

    # Try to install all of the generated requirements.
    # FIXME: This takes WAY to long.
    install_requirement(requirements, local_repos=local_repos,
        remote_repos=remote_repos, interactive=interactive, dry_run=dry_run,
        term_width=term_width, verbose=verbose)

    # After we have finished the update, we save the new state.
    # TODO:  If the update failed, we should instead revert to the
    #        previous state.
    save_state(verbose=verbose)


def date_display_diff(recent, old):
    """
    The two inputs are time tuples for dates and this function will return a simple date
    display difference between the two time tuples.
    """
    # Construct simple datetime.date objects which only contain year/month/day
    # and from this we can subtact these objects, which yields a
    # datetime.timedelta object.  The datetime.timedelta object only keeps
    # track of days in difference so we need to calculate the years, months,
    # weeks and day difference.
    # Note: This makes an assumption based on the average number of days
    #       in a month being 30.  We don't need to be exactly precise since
    #       this display date is just meant to offer a simple display.
    date_diff = (datetime.date(recent[0], recent[1], recent[2])
                 - datetime.date(old[0], old[1], old[2]))
    years, days = divmod(date_diff.days, 365)
    months, days = divmod(days, 30)
    weeks, days = divmod(days, 7)

    # Determine the simple display date based on the years, months, weeks,
    # and days difference that was calculated.
    date_display = ""
    if years:
        if years == 1:
            date_display = "Last year"
        else:
            date_display = "%s years ago" % years
    elif months:
        if months == 1:
            date_display = "Last month"
        else:
            date_display = "%s months ago" % months
    elif weeks:
        if weeks == 1:
            date_display = "Last week"
        else:
            date_display = "%s weeks ago" % weeks
    elif days:
        if days == 1:
            date_display = "Yesterday"
        else:
            date_display = "%s days ago" % days
    else:
        date_display = "Today"

    # Finally, return the calculated display date.
    return date_display


def rollback_menu(remote_repos=None, interactive=True,
    dry_run=False, term_width=0, show_all=False, num_entries=5,
    show_dates=False):
    """
    Show a menu with possible rollback options and perform the appropriate
    action based on the user's input.
    """
    # Create a list of metadata for the possible rollback dates so that we
    # can create an auto-generated user selection layout.  Based on the
    # command-line options, we can limit the list of rollback points that
    # are shown.  If the enstaller.cache doesn't exist, let the user know
    # why they can not do a rollback.
    cached_states = retrieve_states()
    if not cached_states:
        print ("A rollback can not be performed because there are "
            "no cached rollback points.")
        return
    if not show_all:
        cached_states = cached_states[:num_entries]
    metadata = []
    local_time = time.localtime()
    for i, state in enumerate(cached_states):
        # Create a date display from the difference between the timestamp of
        # the rollback point and the current time.  The difference we retrieve
        # is the time sine the epoch (i.e. January 1, 1970), so we make our
        # calculations from that.
        timestamp = state[0]
        time_tuple = time.strptime(timestamp, "%Y%m%d%H%M%S")
        date_display = date_display_diff(local_time, time_tuple)

        # If the user specified to display the full date/timestamp with the
        # rollback points, then tack it onto the simple display.
        if show_dates:
            date_display = "%s (%s)" % (date_display,
                                        time.strftime("%Y/%m/%d %H:%M:%S",
                                                      time_tuple))

        # Find the differences between two rollback points (i.e. packages
        # added, removed, or modified) and calculate a nice diff that can
        # be displayed in the table.
        # We need to stop calculating these diffs once we reach the last
        # item though because there are no entries after it.
        option_diff = ""
        if i < len(cached_states)-1:
            project_list_1 = cached_states[i][1]
            project_list_2 = cached_states[i+1][1]
            diff_list_1 = [project for project in project_list_1
                           if not project in project_list_2]
            diff_list_2 = [project for project in project_list_2
                           if not project in project_list_1]
            if len(diff_list_1) == 0 and len(diff_list_2) == 0:
                option_diff = "  There are no changes between these points."
            else:
                added = []
                modified = []
                deactivated = []
                for project in diff_list_1:
                    (project_name_1,
                     project_version_1) = parse_project_str(project)
                    found = False

                    for project2 in diff_list_2:
                        (project_name_2,
                         project_version_2) = parse_project_str(project2)
                        if project_name_1 == project_name_2:
                            found = True
                            modified.append("%s-%s to %s" % (
                                    project_name_1, project_version_2,
                                project_version_1))
                            break

                    if not found:
                        added.append("%s-%s" % (project_name_1,
                                                project_version_1))
                for project2 in diff_list_2:
                    (project_name_2,
                     project_version_2) = parse_project_str(project2)
                    found = False
                    for project in diff_list_1:
                        (project_name_1,
                         project_version_1) = parse_project_str(project)
                        if project_name_2 == project_name_1:
                            found = True
                            break

                    if not found:
                        deactivated.append("%s-%s" % (project_name_2,
                                                      project_version_2))
                if len(added) > 0:
                    option_diff += "  [A] %s" % added[0]
                    for add_str in added[1:]:
                        option_diff += "\n\t      %s" % add_str
                    if len(modified) > 0 or len(deactivated) > 0:
                        option_diff += "\n\t"
                if len(modified) > 0:
                    option_diff += "  [M] %s" % modified[0]
                    for mod_str in modified[1:]:
                        option_diff += "\n\t      %s" % mod_str
                    if len(deactivated) > 0:
                        option_diff += "\n\t"
                if len(deactivated) > 0:
                    option_diff += "  [D] %s" % deactivated[0]
                    for deac_str in deactivated[1:]:
                        option_diff += "\n\t      %s" % deac_str

        # Set the 'date' metadata according to the date display and
        # the differene between rollback points.
        metadata.append({"date": date_display + "\n\t" + option_diff})

    # If a user selects to view more information about a specific rollback
    # point, keep prompting the user to choose a rollback point after
    # displaying that information.
    while True:
        selection = user_select(["date"],
            metadata, ("Select a restore point to rollback your "
            "environment to.  For more information about a "
            "specific rollback point, type the option number "
            "followed by a question mark.  Use '0' to cancel "
            "rollback:  "), default="0", extra_char="?",
            max_width=term_width)
        if not selection.endswith("?"):
            break
        else:
            option = int(selection.split('?')[0])-1
            state = cached_states[option]
            timestamp = state[0]
            time_tuple = time.strptime(timestamp, "%Y%m%d%H%M%S")
            date_display = time.strftime("%Y/%m/%d %H:%M:%S", time_tuple)
            print "Active Project State on %s:" % date_display
            state_data=[]
            project_list = state[1]
            for project in project_list:
                (project_name, project_version) = parse_project_str(project)
                state_data.append({"project_name": project_name,
                    "version": project_version})
            msg = rst_table(["project_name", "version"],
                state_data, sorted=False, max_width=term_width)
            msg += "\n\n"
            print msg

    # If the user selected option '0', then there's nothing to do.
    if selection == '0':
        return

    # Now that the user has selected a rollback point, perform the action
    # to rollback to that state.  Once the rollback has been completed
    # successfully, let the user know.
    state_index = int(selection)-1
    project_list = cached_states[state_index][1]
    rollback_state(project_list, remote_repos, interactive, dry_run, term_width)
    timestamp = cached_states[state_index][0]
    time_tuple = time.strptime(timestamp, "%Y%m%d%H%M%S")
    date_display = time.strftime("%Y/%m/%d %H:%M:%S", time_tuple)
    print "\nSystem successfully rolled back to state on: %s" % date_display


def list_installed(interactive=True, term_width=0):
    repos = get_local_repos()
    for repo in repos:
        repo.build_package_list()

        # Pretty print repo information
        print repo.location
        print "="*len(repo.location)
        print
        if repo.projects:
            if interactive:
                print repo.pretty_packages(max_width=term_width)
            else:
                print repo.pretty_packages()
            print
        else:
            print "No packages installed"
        print


def setup_parser():
    description = """\
Utility for managing packages in the site-packages directory.
The command needs to be one of the following: install, upgrade, update,
rollback, remove, list, save_state
"""

    parser = OptionParser(usage="usage: enpkg command [options]",
                          description=description,
                          version="Enstaller version %s" % __version__)

    term_width = 80
    try:
        import fcntl, termios, struct
        # yuck! really should make the interactive stuff a curses app
        data = fcntl.ioctl(sys.stdin.fileno(), termios.TIOCGWINSZ, '1234')
        term_width = struct.unpack('hh', data)[1]
    except ImportError:
        pass

    parser.set_defaults(interactive=False, logging=INFO, dry_run=False,
        term_width=term_width, allow_unstable=False, proxy="", find_links=[],
        show_all=False, num_entries=5, show_dates=False)

    parser.add_option("-a", "--show-all",
        action="store_true", dest="show_all",
        help="show all rollback point entries")
    parser.add_option("-d", "--dry-run",
        action="store_true", dest="dry_run",
        help="perform a dry-run without changing installed setup")
    parser.add_option("-f", "--find-links",
        action="append", type="string", dest="find_links",
        help="add location to look for packages")
    parser.add_option("-i", "--interactive",
        action="store_true", dest="interactive",
        help="prompt user for choices")
    parser.add_option("-n", "--num-entries",
        action="store", type="int", dest="num_entries",
        help="number of rollback point entries to show")
    parser.add_option("--proxy",
        action="store", type="string", dest="proxy",
        help="use a proxy for downloads")
    parser.add_option("-q", "--quiet",
        action="store_const", const=WARNING, dest="logging")
    parser.add_option("--show-dates",
        action="store_true", dest="show_dates",
        help="show the dates and timestamps for rollback entries")
    #parser.add_option("-u", "--allow-unstable",
    #    action="store_true", dest="allow_unstable",
    #    help="search unstable repositories")
    parser.add_option("-v", "--verbose",
        action="store_const", const=DEBUG, dest="logging")
    parser.add_option("-w", "--width",
        action="store", type="int", dest="term_width",
        help="set the width of the terminal window")
    return parser


def main():

    # Get and validate our options and arguments
    parser = setup_parser()
    options, args = parser.parse_args()
    if len(args) < 1:
        parser.error("Must call enpkg with one of 'install', 'upgrade', "
                     "'update', 'rollback', 'remove', 'save_state', or "
                     "'list', see -h for more details")

    # Set up logging
    basicConfig(level=options.logging, format="%(message)s")

    # Setup our verbosity.  We are verbose only if logging is DEBUG level.
    options.verbose = (DEBUG == options.logging)

    # Build our list of remote repositories we'll search for distributions to
    # install.  Any repository settings provided via the command line take
    # precedence over anything in the config file, and the index in the config
    # file always comes last.  This ordering is important because we now stop
    # as soon as we find a matching distribution in the first repository.
    remote_repos = [HTMLRepository(arg, verbose=options.verbose) for arg in
        options.find_links]
    remote_repos.extend([HTMLRepository(u, verbose=options.verbose) for u in
        get_configured_repos(unstable=options.allow_unstable,
        verbose=options.verbose)])
    remote_repos.append(HTMLRepository(get_configured_index(), index=True,
        verbose=options.verbose))

    # Try to set up a proxy server, either from options or environment vars.
    # This makes urllib2 calls do the right thing.
    try:
        installed = setup_proxy(options.proxy)
    except ValueError, e:
        error('Proxy configuration error: %s' % e)
        sys.exit(2)

    # Do the user's requested command.
    command = args[0]
    args = args[1:]

    if command == "install":
        install_requirement([Requirement.parse(arg) for arg in args],
            remote_repos=remote_repos,
            interactive=options.interactive, dry_run=options.dry_run,
            term_width=options.term_width)

    elif command == "upgrade":
        upgrade_project(args,
            remote_repos=remote_repos,
            interactive=options.interactive, dry_run=options.dry_run,
            term_width=options.term_width, verbose=options.verbose)

    elif command == "update":
        update_project(args,
            remote_repos=remote_repos,
            interactive=options.interactive, dry_run=options.dry_run,
            term_width=options.term_width, verbose=options.verbose)

    elif command == "rollback":
        rollback_menu(remote_repos=remote_repos,
            interactive=options.interactive, dry_run=options.dry_run,
            term_width=options.term_width, show_all=options.show_all,
            num_entries=options.num_entries, show_dates=options.show_dates)

    elif command == "save_state":
        save_state(verbose=options.verbose)

    elif sys.argv[1] == "activate":
        # Before we do anything, save the current working state of the
        # environment to a rollback point.
        save_state(verbose=options.verbose)
        install_requirement([Requirement.parse(arg) for arg in args],
            remote_repos=[], interactive=options.interactive,
            dry_run=options.dry_run, term_width=options.term_width)
        # After we have finished the activate, we save the new state.
        save_state(verbose=options.verbose)

    elif sys.argv[1] == "deactivate":
        # Before we do anything, save the current working state of
        # the environment to a rollback point.
        save_state(verbose=options.verbose)
        deactivate_requirement([Requirement.parse(arg) for arg in args],
            interactive=options.interactive, dry_run=options.dry_run)
        # After we have finished the deactivate, we save the new state.
        save_state(verbose=options.verbose)

    elif command == "remove":
        # Before we do anything, save the current working state of
        # the environment to a rollback point.
        save_state(verbose=options.verbose)
        remove_requirement([Requirement.parse(arg) for arg in args],
            interactive=options.interactive, dry_run=options.dry_run)
        # After we have finished the remove, we save the new state.
        save_state(verbose=options.verbose)

    elif command == "list":
        list_installed(interactive=options.interactive,
            term_width=options.term_width)


def _main():
    import cProfile, pstats, StringIO
    prof = cProfile.Profile()
    prof = prof.runctx("real_main()", globals(), locals())
    stream = StringIO.StringIO()
    stats = pstats.Stats(prof, stream=stream)
    stats.sort_stats("time")
    stats.print_stats(80)
    print "Profile data:\n%s" % stream.getvalue()


if __name__ == "__main__":
    main()
    sys.exit()
