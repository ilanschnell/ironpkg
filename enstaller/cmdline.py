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
import sys
import os
from optparse import OptionParser
from logging import basicConfig, error, warning, info, debug, DEBUG, INFO, \
    WARNING, ERROR

# third party module imports
from pkg_resources import Requirement

# enstaller imports
from package import EasyInstallPackage, RemotePackage
from repository import EasyInstallRepository, HTMLRepository, RepositoryUnion
from utilities import remove_eggs_from_path, rst_table, get_platform
from upgrade import upgrade
from proxy.api import setup_proxy


try:
    from enstaller import __version__
except ImportError:
    from __init__ import __version__


# set up global variables
PLAT, PLAT_VER = get_platform()

ENTHOUGHT_REPO = (
    "http://code.enthought.com/enstaller/eggs/%s/%s" % (PLAT, PLAT_VER))

ENTHOUGHT_UNSTABLE_REPO = (
    "http://code.enthought.com/enstaller/eggs/%s/%s/unstable" %
    (PLAT, PLAT_VER))

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
    # is there a better way than this?
    site_packages = [path for path in sys.path
                     if path.endswith('site-packages')]
    if site_packages:
        return EasyInstallRepository(location=site_packages[0])
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


def user_select(header, data, prompt, default="1", max_width=0):
    """Present a collection of options to the user and return a response
    """

    valid_responses = [str(i+1) for i in range(len(data))]
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
        return int(response)-1
    else:
        return None


def upgrade_project(keys, local_repos=None, remote_repos=None, interactive=True,
    dry_run=False, term_width=0):
    """ Upgrade a project, if possible.
    """
    if local_repos == None:
        local_repos = get_local_repos()
    local = RepositoryUnion(get_local_repos())
    requirements = []
    for key in keys:
        active_local_projects = [project
            for project in local.projects[key].projects
                if project.active]
        if active_local_projects:
            pkg = active_local_projects[0].active_package
            requirement = Requirement.parse("%s>%s" % (key, pkg.version))
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

def install_requirement(requirements, target_repo=None, local_repos=None,
        remote_repos=None, interactive=True, dry_run=False, verbose=False,
        term_width=0):
    """Find and install packages which match the requirements, upgradeing or
    downgrading packages when needed.
    """
    if target_repo is None:
        target_repo = get_site_packages()
    if remote_repos is None:
        remote_repos = [HTMLRepository("http://code.enthought.com/"),
            HTMLRepository("http://pypi.python.org/simple")]
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
        packages = [package
            for package in available.projects[requirement.key].packages
                if package.distribution in requirement]
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

    parser = OptionParser(usage="usage: enpgk command [options]",
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
        term_width=term_width, remote_html=[PYPI_REPO],
        find_links=[ENTHOUGHT_REPO], remote_xmlrpc=[],
        allow_unstable=False, proxy="")

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
    # get our options
    parser = setup_parser()
    options, args = parser.parse_args()

    if len(args) < 1:
        parser.error("Must call enpkg with one of 'install', 'upgrade', "
                     "'remove', or 'list', see -h for more details")

    # set up logging
    basicConfig(level=options.logging, format="%(message)s")

    # warn the user if the detected platform may not be supported
    supported = ["windows", "macosx", "debian", "rhel", "suse", "ubuntu"]

    if PLAT not in supported or PLAT_VER == "":
        msg = """
        Warning: There may not be an Enthought repository for
        platform "%s" "%s".
        Check

            http://code.enthought.com/enstaller/eggs

        for the available platforms.
        """ % (PLAT, PLAT_VER)

        warning(msg)

    if options.allow_unstable:
        options.find_links.append(ENTHOUGHT_UNSTABLE_REPO)
    remote_repos=[HTMLRepository(arg) for arg in options.remote_html]
    # XXX hack!  Should make the find_packages part of the Repository object
    remote_repos[0].environment.add_find_links(options.find_links)

    try:
        # try to set up a proxy server, either from options or environment
        # this makes urllib2 calls do the right thing
        installed = setup_proxy(options.proxy)
    except ValueError, e:
        error('Proxy configuration error: %s' % e)
        sys.exit(2)

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
