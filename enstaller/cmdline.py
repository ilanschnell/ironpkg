#------------------------------------------------------------------------------
# Copyright (c) 2008, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#
# Corran Webster
#------------------------------------------------------------------------------


# standard library imports
from distutils import sysconfig
import sys
import os
from optparse import OptionParser
from logging import basicConfig, error, warning, info, debug, DEBUG, INFO, \
    WARNING, ERROR
import time

# third party module imports
from pkg_resources import Requirement

# enstaller imports
from config import get_configured_repos
from package import EasyInstallPackage, RemotePackage
from proxy.api import setup_proxy
from repository import EasyInstallRepository, HTMLRepository, RepositoryUnion
from rollback import retrieve_states, rollback_state, save_state
from upgrade import upgrade
from utilities import remove_eggs_from_path, rst_table, get_platform


try:
    from enstaller import __version__
except ImportError:
    from __init__ import __version__


# set up global variables
PLAT, PLAT_VER = get_platform()
PYPI_REPO = "http://pypi.python.org/simple"


def get_local_repos():
    """Find all easy_install repositories on sys.path
    """
    repos = []
    for dirname in remove_eggs_from_path(sys.path):
        if os.path.exists(os.path.join(dirname, "easy-install.pth")):
            repo = EasyInstallRepository(location=dirname)
            repos.append(repo)
    return repos


def get_site_packages():
    """Find the site-packages directory
    """
    site_packages = sysconfig.get_python_lib()
    if site_packages:
        return EasyInstallRepository(location=site_packages)
    else:
        error("Can't locate site-packages directory in path.")


def query_user(msg, default=""):
    """Present a yes/no question to the user and return a response
    """

    if default:
        msg += "[%s] " % default
    response = ""
    while len(response) == 0 or response[0] not in "yn":
        response = raw_input(msg).strip().lower()
        if response == "" and default:
            response = default
    return response[0] == "y"


def user_select(header, data, prompt, default="1", extra_char=None,
    max_width=0):
    """Present a collection of options to the user and return a response
    """

    valid_responses = [str(i+1) for i in range(len(data))]
    if extra_char:
        valid_responses += [(str(i+1)+extra_char) for i in range(len(data))]
    for i, row in enumerate(data):
        row["option"] = str(i+1).rjust(5)
    header = ["option"] + header
    msg = rst_table(header, data, sorted=False, max_width=max_width)
    #msg = "\n".join("%4s. %s" % (i+1, option)
    #                for i, option in enumerate(option_list))
    msg += "\n\n"
    msg += prompt + "[%s] " % default
    response = ""
    while len(response) == 0 or response not in valid_responses:
        response = raw_input(msg).strip().lower()
        if response == "" and default:
            response = default
    if response != "none":
        if extra_char:
            return response
        else:
            return int(response)-1
    else:
        return None


def upgrade_project(keys, local_repos=None, remote_repos=None,
    interactive=True, dry_run=False, term_width=0):
    """ Upgrade a project, if possible.
    """
    # Before we do anything, save the current working state of the environment to a rollback point.
    # TODO:  If the upgrade fails, we need to rollback to this save point.
    save_state()
    
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
        
        active_local_projects = [project
            for project in local.projects[key].projects
                if project.active]
        if active_local_projects:
            pkg = active_local_projects[0].active_package

            # Split up the version string into a list so we can determine
            # upgrades in the major/minor version parts.  Also check to see
            # if the package has our build number tag.
            version = pkg.version
            if version[-2:] == "_s":
                version = version[-2:]
            version_parts = version.split('.')

            # This upgrade could be done on packages the user installed that
            # we(Enthought) didn't build (i.e. no build number tag), so we
            # need to account for this.  So, if the last part of the version
            # string is 4 digits long, we will assume that is our build number
            # tag.
            try:
                major = int(version_parts[0])
            except ValueError:
                # FIXME:  Currently, if we fail to convert part of the version
                # string to an integer, we just skip trying to upgrade the
                # package.  This occurs when packages have characters in their
                # versions, such as pytz-2008c.
                continue
            if len(version_parts[-1]) == 4:
                # Installed package:  foo-1.0001 or foo-1.0.0001
                # Upgrade needs:  foo>=2.0001 or foo>=2.0.0001
                if len(version_parts) < 4:
                    req_ver = str(major+1)
                    for a in range(len(version_parts)-2):
                        req_ver += '.0'
                # Installed package:  foo-1.0.0.0001, or more parts
                # Upgrade needs:  foo>=1.1.0.0001, etc...
                else:
                    try:
                        minor = int(version_parts[1])
                    except ValueError:
                        # FIXME:  Currently, if we fail to convert part of the
                        # version string to an integer, we just skip trying to
                        # upgrade the package.  This occurs when packages have
                        # characters in their versions, such as pytz-2008c.
                        continue
                    req_ver = str(major) + '.' + str(minor+1)
                    for a in range(len(version_parts)-3):
                        req_ver += '.0'
                req_ver += '.0001'
                req_str = "%s>=%s" % (key, req_ver)
            else:
                # Installed package:  foo-1
                # Upgrade needs:  foo>1
                if len(version_parts) == 1:
                    req_str = "%s>%s" % (key, version)
                # Installed package:  foo-1.0
                # Upgrade needs:  foo>=2.0
                elif len(version_parts) == 2:
                    req_ver = str(major+1) + '.0'
                # Installed package:  foo-1.0.0, or more parts
                # Upgrade needs:  foo>=1.1.0, etc...
                else:
                    try:
                        minor = int(version_parts[1])
                    except ValueError:
                        # FIXME:  Currently, if we fail to convert part of the
                        # version string to an integer, we just skip trying to
                        # upgrade the package.  This occurs when packages have
                        # characters in their versions, such as pytz-2008c.
                        continue
                    req_ver = str(major) + '.' + str(minor+1)
                    for a in range(len(version_parts)-2):
                        req_ver += '.0'
                req_str = "%s>=%s" % (key, req_ver)

            # Create a requirement object from our requirement string.
            requirement = Requirement.parse(req_str)
        else:
            max_pkg = None
            for pkg in local.projects[key].packages:
                if max_pkg is None or pkg > max_pkg:
                    max_pkg = pkg
            if max_pkg is not None:
                requirement = Requirement.parse("%s>%s" % (key,
                    max_pkg.version))
            else:
                requirement = Requirement.parse(project)
        requirements.append(requirement)

    print requirements

    install_requirement(requirements, local_repos=local_repos,
        remote_repos=remote_repos, interactive=interactive, dry_run=dry_run,
        term_width=term_width)

    
def update_project(keys, local_repos=None, remote_repos=None,
    interactive=True, dry_run=False, term_width=0):
    """ Update a project, if possible.
    """
    # Before we do anything, save the current working state of the environment to a rollback point.
    # TODO:  If the upgrade fails, we need to rollback to this save point.
    save_state()
    
    if local_repos == None:
        local_repos = get_local_repos()
    local = RepositoryUnion(get_local_repos())
    requirements = []

    # If no explicit project(s) were specified to update, try to update
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
        
        active_local_projects = [project
            for project in local.projects[key].projects
                if project.active]
        if active_local_projects:
            pkg = active_local_projects[0].active_package

            # Split up the version string into a list so we can determine
            # updates in the patch/build version parts.  Also check to see
            # if the package has our build number tag.
            version = pkg.version
            if version[-2:] == "_s":
                version = version[-2:]
            version_parts = version.split('.')

            # This update could be done on packages the user installed that
            # we(Enthought) didn't build (i.e. no build number tag), so we
            # need to account for this.  So, if the last part of the version
            # string is 4 digits long, we will assume that is our build number
            # tag.
            try:
                major = int(version_parts[0])
            except ValueError:
                # FIXME:  Currently, if we fail to convert part of the version
                # string to an integer, we just skip trying to upgrade the
                # package.  This occurs when packages have characters in their
                # versions, such as pytz-2008c.
                continue
            if len(version_parts[-1]) == 4:
                # Installed package:  foo-1.0001 or foo-1.0.0001
                # Update needs:  foo>1.0001, <2.0001 or foo>1.0.0001, <2.0.0001
                if len(version_parts) < 4:
                    max_req_ver = str(major+1)
                    for a in range(len(version_parts)-2):
                        max_req_ver += '.0'
                # Installed package:  foo-1.0.0.0001, or more parts
                # Update needs:  foo>1.0.0.0001, <1.1.0.0001, etc...
                else:
                    try:
                        minor = int(version_parts[1])
                    except ValueError:
                        # FIXME:  Currently, if we fail to convert part of the
                        # version string to an integer, we just skip trying to
                        # upgrade the package.  This occurs when packages have
                        # characters in their versions, such as pytz-2008c.
                        continue
                    max_req_ver = str(major) + '.' + str(minor+1)
                    for a in range(len(version_parts)-3):
                        max_req_ver += '.0'
                max_req_ver += '.0001'
                req_str = "%s>%s, <%s" % (key, version, max_req_ver)
            else:
                # Installed package:  foo-1
                # Unable to update because only possible change is a major
                # version bump.
                if len(version_parts) == 1:
                    continue
                # Installed package:  foo-1.0
                # Update needs:  foo>1.0, <2.0
                elif len(version_parts) == 2:
                    req_ver = str(major+1) + '.0'
                # Installed package:  foo-1.0.0, or more parts
                # Update needs:  foo>1.0.0, <1.1.0, etc...
                else:
                    try:
                        minor = int(version_parts[1])
                    except ValueError:
                        # FIXME:  Currently, if we fail to convert part of the
                        # version string to an integer, we just skip trying to
                        # upgrade the package.  This occurs when packages have
                        # characters in their versions, such as pytz-2008c.
                        continue
                    max_req_ver = str(major) + '.' + str(minor+1)
                    for a in range(len(version_parts)-2):
                        max_req_ver += '.0'
                req_str = "%s>%s, <%s" % (key, version, max_req_ver)

            # Create a requirement object from our requirement string.
            requirement = Requirement.parse(req_str)
        else:
            max_pkg = None
            for pkg in local.projects[key].packages:
                if max_pkg is None or pkg > max_pkg:
                    max_pkg = pkg
            if max_pkg is not None:
                requirement = Requirement.parse("%s>%s" % (key,
                    max_pkg.version))
            else:
                requirement = Requirement.parse(project)
        requirements.append(requirement)

    print requirements

    install_requirement(requirements, local_repos=local_repos,
        remote_repos=remote_repos, interactive=interactive, dry_run=dry_run,
        term_width=term_width)
        

def rollback_menu(term_width=0):
    """
    Show a menu with possible rollback options and perform the appropriate
    action based on the user's input.
    """
    # Create a list of metadata for the possible rollback dates so that we can create an
    # auto-generated user selection layout.
    cached_states = retrieve_states()
    metadata = []
    for state in cached_states:
        timestamp = state[0]
        time_tuple = time.strptime(timestamp, "%Y%m%d%H%M%S")
        date_display = time.strftime("%Y/%m/%d %H:%M:%S", time_tuple)
        metadata.append({"date": date_display})
        
    # If a user selects to view more information about a specific rollback point, keep
    # prompting the user to choose a rollback point after displaying that information.
    while True:
        selection = user_select(["date"],
            metadata, ("Select a restore point to rollback your "
            "environment to.\nFor more information about a "
            "specific rollback point,\ntype the option number "
            "followed by a question mark:  "), extra_char="?",
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
                post_install_flag = False
                if project.endswith('-s'):
                    project = project[:-2]
                    post_install_flag = True
                project_split = project.split('-')
                project_name = '-'.join(project_split[:-1])
                project_version = project_split[-1]
                if post_install_flag:
                    project_version += '-s'
                state_data.append({"project_name": project_name,
                    "version": project_version})
            msg = rst_table(["project_name", "version"],
                state_data, sorted=False, max_width=term_width)
            msg += "\n\n"
            print msg
            
    # Now that the user has selected a rollback point, perform the action to rollback
    # to that state.  Once the rollback has been completed successfully, let the user
    # know.
    state_index = int(selection)-1
    project_list = cached_states[state_index][1]
    rollback_state(project_list)
    timestamp = cached_states[state_index][0]
    time_tuple = time.strptime(timestamp, "%Y%m%d%H%M%S")
    date_display = time.strftime("%Y/%m/%d %H:%M:%S", time_tuple)
    print "\nSystem successfully rolled back to state on: %s" % date_display


def install_requirement(requirements, target_repo=None, local_repos=None,
        remote_repos=None, interactive=True, dry_run=False, verbose=False,
        term_width=0):
    """Find and install packages which match the requirements, upgradeing or
    downgrading packages when needed.
    """
    if target_repo is None:
        target_repo = get_site_packages()
    if remote_repos is None:
        remote_repos = [HTMLRepository("http://pypi.python.org/simple")]
    if local_repos is None:
        local_repos = get_local_repos()
    local = RepositoryUnion(get_local_repos())
    available = RepositoryUnion(local_repos+remote_repos)

    # generate proposals
    installed = dict((key, project.active_package)
                     for key, project in local.projects.items()
                     if project.active_package != None)
    to_install = []
    for requirement in requirements:
        try:
            packages = [package
                for package in available.projects[requirement.key].packages
                    if package.distribution in requirement]
        except KeyError:
            print "Could not find suitable distribution for %s" % requirement
            return
        if not packages:
            warning("Could not find a package which matches requirement %s" %
                    requirement)
            continue
        if interactive and len(packages) > 1:
            selection = user_select(["version", "active", "location"],
                [pkg.metadata for pkg in packages], "Select package: ",
                max_width=term_width)

            #selection = user_select(["Package '%s' at %s%s" % (pkg.name,
            #    pkg.location, " (Active)" if pkg.active else "")
            #    for pkg in packages], "Select package: ")
            if selection == None:
                info("User selected no package for requirement %s" %
                     requirement)
                continue
            package = packages[selection]
        else:
            package = packages[0]

        if package.active:
            # nothing to do
            info("Package %s satisfies %s and is already active" %
                (package.name, requirement))
        else:
            to_install.append(package)

    if not to_install:
        return

    upgrades = upgrade(to_install, installed, available)
    try:
        proposal, reasoning = upgrades.next()
    except StopIteration:
        info("Unable to create a consistent installation plan.")
        return

    if interactive:
        response = False
        while not response:
            print
            print "Proposal:"
            for project, package in proposal.items():
                if package.active:
                    continue
                for repo in local_repos:
                    if project in repo and repo[project].active:
                        active_project = repo[project]
                        break
                else:
                    active_project = None

                if active_project is None:
                    print ("  Install %s from %s" % (package.name,
                        package.location))[:term_width]
                else:
                    print ("  Upgrade %s from %s to %s from %s" % (
                        active_project.name,
                        active_project.active_package.version, package.version,
                        package.location))[:term_width]
            response = query_user("Accept proposed installation plan (y/n)? ",
                                  default="y")
            if not response:
                try:
                    proposal, reasoning = upgrades.next()
                except StopIteration:
                    info("No proposed installation plan was acceptable "
                         "to the user.")
                    return

    # first activate any local packages
    active_environments = set()
    for key, package in proposal.items():
        if isinstance(package, EasyInstallPackage):
            package.activate(save=False, dry_run=dry_run)
            active_environments.add(package.repository.active)
    for env in active_environments:
        if not dry_run:
            env.save()
        else:
            print "Saving .pth file."

    for key, package in proposal.items():
        if isinstance(package, RemotePackage):
            package.install(target_repo, dry_run=dry_run)


def remove_requirement(requirements, repos=None, interactive=False,
        dry_run=False):
    """Remove all installed packages which match the requirements
    """
    if repos is None:
        repos = get_local_repos()
    for requirement in requirements:
        removed = False
        for repo in repos:
            if requirement.key not in repo.projects:
                continue
            for package in repo.projects[requirement.key].packages:
                if package.distribution in requirement:
                    removed = True
                    if interactive:
                        for dep in sorted(package.full_dependent_packages,
                                key=lambda x: x.name):
                            print "Package %s depends on %s" % (dep.name,
                                package.name)
                        response = query_user("Remove '%s' from %s (y/n)? " %
                                              (package.name,
                                               package.repository.location),
                                              default="y")
                        if not response:
                            continue
                    package.remove(dry_run=dry_run)
        if not removed:
            warning("Found no requirement which matches %s" % requirement)

def deactivate_requirement(requirements, repos=None, interactive=False,
        dry_run=False):
    if repos is None:
        repos = get_local_repos()
    for requirement in requirements:
        deactivated = False
        for repo in repos:
            for package in repo.active_packages:
                if package.distribution in requirement:
                    deactivated = True
                    if interactive:
                        response = query_user("Deactivate '%s' from %s (y/n)? "
                                              % (package.name,
                                                 package.repository.location),
                                              default="y")
                        if not response:
                            continue
                    package.deactivate(dry_run=dry_run)
        if not deactivated:
            warning("Found no requirement which matches %s" % requirement)


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
The command needs to be on of the following: install, upgrade, remove, list
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
        term_width=term_width, remote_html=[PYPI_REPO], remote_xmlrpc=[],
        allow_unstable=False, proxy="", find_links=[])

    parser.add_option("-i", "--interactive", action="store_true",
        dest="interactive", help="prompt user for choices")
    parser.add_option("-v", "--verbose", action="store_const", const=DEBUG,
        dest="logging")
    parser.add_option("-q", "--quiet", action="store_const", const=WARNING,
        dest="logging")
    parser.add_option("-d", "--dry-run", action="store_true", dest="dry_run",
        help="perform a dry-run without changing installed setup")
    parser.add_option("-w", "--width", action="store", type="int",
        dest="term_width", help="set the width of the terminal window")
    parser.add_option("-r", "--remote-html", action="append", type="string",
        dest="remote_html", help="add a remote HTML-based repository")
    parser.add_option("-x", "--remote-xmlrpc", action="append", type="string",
        dest="remote_xmlrpc", help="add a remote XMLRPC-based repository")
    parser.add_option("-f", "--find-links", action="append", type="string",
        dest="find_links", help="add location to look for packages")
    parser.add_option("-u", "--allow-unstable", action="store_true",
        dest="allow_unstable", help="search unstable repositories")
    parser.add_option("--proxy", action="store", type="string",
        dest="proxy", help="use a proxy for downloads")
    return parser


def main():

    # Get and validate our options and arguments
    parser = setup_parser()
    options, args = parser.parse_args()
    if len(args) < 1:
        parser.error("Must call enpkg with one of 'install', 'upgrade', "
            "'update', 'rollback', 'remove', or 'list', see -h for more details")

    # Set up logging
    basicConfig(level=options.logging, format="%(message)s")

    # Build the list of remote repositories we'll search for distributions to
    # install.  Note that we include any repos specified in our config file but
    # that list depends on whether the user requested "unstable" repos or not.
    remote_repos=[HTMLRepository(arg) for arg in options.remote_html]
    # XXX hack!  Should make the find_packages part of the Repository object
    remote_repos[0].environment.add_find_links(options.find_links)
    remote_repos.extend([HTMLRepository(arg) for arg in
        get_configured_repos(unstable=options.allow_unstable)])

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
            term_width=options.term_width)
    elif command == "update":
        update_project(args,
            remote_repos=remote_repos,
            interactive=options.interactive, dry_run=options.dry_run,
            term_width=options.term_width)
    elif command == "rollback":
        rollback_menu(term_width=options.term_width)
    elif sys.argv[1] == "activate":
        install_requirement([Requirement.parse(arg) for arg in args],
            remote_repos=[], interactive=options.interactive,
            dry_run=options.dry_run, term_width=options.term_width)
    elif sys.argv[1] == "deactivate":
        deactivate_requirement([Requirement.parse(arg) for arg in args],
            interactive=options.interactive, dry_run=options.dry_run)
    elif command == "remove":
        remove_requirement([Requirement.parse(arg) for arg in args],
            interactive=options.interactive, dry_run=options.dry_run)
    elif command == "list":
        list_installed(interactive=options.interactive,
            term_width=options.term_width)


if __name__ == "__main__":
    main()
    sys.exit()
