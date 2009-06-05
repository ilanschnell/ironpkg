#------------------------------------------------------------------------------
# Copyright (c) 2008, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#------------------------------------------------------------------------------


import os
import sys

from distutils import sysconfig
from enstaller.package import EasyInstallPackage, RemotePackage
from enstaller.repository import EasyInstallRepository, HTMLRepository, RepositoryUnion
from enstaller.upgrade import upgrade
from enstaller.utilities import remove_eggs_from_path, user_select, query_user
from logging import error, warning, info


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
        

def install_requirement(requirements, target_repo=None, local_repos=None,
        remote_repos=None, interactive=True, dry_run=False, verbose=False,
        term_width=0):
    """\
    Find and install packages which match the requirements.
    
    This may either upgrade or downgrade packages when needed.

    """
    if target_repo is None:
        target_repo = get_site_packages()
    if remote_repos is None:
        remote_repos = [HTMLRepository("http://pypi.python.org/simple")]
    if local_repos is None:
        local_repos = get_local_repos()
    # FIXME: DMP why did we not use the specified set of local repos?
    # Commenting out for now.
    #local = RepositoryUnion(get_local_repos())
    local = RepositoryUnion(local_repos)
    available = RepositoryUnion(local_repos+remote_repos)

    # Generate proposals
    installed = dict((key, project.active_package) for key, project in \
        local.projects.items() if project.active_package != None)
    to_install = []
    for requirement in requirements:

        # Ensure we can find at least one distribution matching the 
        # requirement.
        try:
            packages = [package
                for package in available.projects[requirement.key].packages
                    if package.distribution in requirement]
        except KeyError:
            if verbose:
                print "Could not find suitable distribution for %s" % \
                    requirement
            # FIXME: Should we really return here?  I guess we're trying to say
            # we couldn't find ANY match for ALL requirements by doing so?
            return
        if not packages:
            if verbose:
                warning("Could not find a package which matches requirement "
                    "%s" % requirement)
            continue

        # If we're running in interactive mode, let the user pick a
        # distribution if there is more than one to pick from.  Otherwise,
        # we just go with the first one.
        if interactive and len(packages) > 1:
            selection = user_select(["version", "active", "location"],
                [pkg.metadata for pkg in packages], "Select package: ",
                max_width=term_width)
            #selection = user_select(["Package '%s' at %s%s" % (pkg.name,
            #    pkg.location, " (Active)" if pkg.active else "")
            #    for pkg in packages], "Select package: ")
            if selection == None:
                if verbose:
                    info("User selected no package for requirement %s" %
                        requirement)
                continue
            package = packages[selection]
        else:
            package = packages[0]

        # If the selected distribution is already active, we have nothing to
        # install.
        if package.active:
            if verbose:
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

