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


# Standard library imports.
from distutils import sysconfig
import os
from time import strftime

# Enstaller imports.
from pkg_resources import Requirement
from requirements import get_site_packages, install_requirement


def parse_project_str(project_str):
    """
    Pass in a project string(i.e. foo-1.0) and return a tuple of the
    (project_name, project_version).  This can be messy depending
    on the presence of a post-install script flag, so this helper function
    relieves some redudancy when needing to parse these strings.
    """
    post_install_flag = False
    if project_str.endswith('-s'):
        project_str = project_str[:-2]
        post_install_flag = True
    project_split = project_str.split('-')
    project_name = '-'.join(project_split[:-1])
    project_version = project_split[-1]
    if post_install_flag:
        project_version += '-s'
    return (project_name, project_version)


def retrieve_states():
    """
    Read the enstaller.cache file to retrieve all of the state entries.
    Return an array of the entries, where each index contains an array
    of two elements.  The first element is the timestamp and the second
    element is the list of package_name-versions.  If the enstaller.cache is
    empty or does not exist, return None.
    """
    # Check if enstaller.cache exists.  If it doesn't, print out an error message and
    # return None.
    site_packages = sysconfig.get_python_lib()
    enstaller_cache = os.path.join(site_packages, 'enstaller.cache')
    if not os.path.exists(enstaller_cache):
        print "The enstaller.cache does not exist."
        return None
        
    # Read in all of the lines from the enstaller.cache.  If the enstaller.cache can not be
    # read, print an error message and return None.  If there are no lines in the
    # enstaller.cache for some reason, print an error message as well.
    file_lines = None
    try:
        f = open(enstaller_cache, 'r')
        file_lines = f.readlines()
        f.close()
    except:
        print "Error in reading the enstaller.cache."
        return None
    if len(file_lines) == 0:
        print ("There are no entries in the enstaller.cache so a "
            "rollback can not be performed.")
        return None
        
    # Iterate through the lines from the enstaller.cache and from this generate the 2D
    # array of timestamps/project_name-versions and then return it after reversing the
    # list so that it is in descending order by timestamp.
    cached_states = []
    for line in file_lines:
        # If for some reason the length of entry_parts is not 2(i.e. a blank line, etc...),
        # then just ignore that line assuming it is erroneous.
        entry_parts = line.strip().split(':')
        if len(entry_parts) != 2:
            continue
        
        timestamp = entry_parts[0]
        pkg_list = entry_parts[1].split(',')
        cached_states.append([timestamp, pkg_list])
    cached_states.reverse()
    return cached_states


def save_state(verbose=False):
    """
    Adds an entry of the current working configuration of packages to the
    enstaller.cache file.
    """
    # Determine the current local repository and from that build a list of the current
    # active packages.
    site_packages = sysconfig.get_python_lib()
    local = get_site_packages()
    active_local_packages = []
    for project in local.projects:
        pkg = local.projects[project].active_package
        if pkg:
            active_local_packages.append(pkg)
            
    # Retrieve a list of project_name-version for the currently active packages.
    # Sort them by name so that we can display them easier.
    project_list = []
    for pkg in active_local_packages:
        project_list.append("%s-%s" % (pkg.project.name, pkg.version))
    project_list.sort()
        
    # Retrieve the most recently saved state and compare it to the current
    # state of the system.  If there have been no changes, then don't bother saving
    # a entry to the enstaller.cache.
    stored_states = retrieve_states()
    if stored_states:
        recent_state = stored_states[0]
        recent_project_list = recent_state[1]
        if project_list == recent_project_list:
            if verbose:
                print ('There is no difference between the current state and '
                    'the most recent saved state in the enstaller.cache, so '
                    'the current state does not need to be saved.')
            return
    
    # Save the current state to an entry in the enstaller.cache file.  Each entry begins
    # with a timestamp, followed by a colon, and then a comma separated list of the
    # project_name-versions for the currently active packages.
    enstaller_cache = os.path.join(site_packages, 'enstaller.cache')
    timestamp = strftime("%Y%m%d%H%M%S")
    pkg_list = ','.join(project_list)
    try:
        if verbose:
            print 'Saving current state...'
        f = open(enstaller_cache, 'a')
        f.write(timestamp + ':')
        f.write(pkg_list)
        f.write('\n')
        f.close()
        if verbose:
            print 'Successfully saved the current state.'
    except:
        print "Error trying to write to the enstaller.cache."
    
    
def rollback_state(project_list, remote_repos=None, interactive=True,
    dry_run=False, term_width=0):
    """
    Input is a list of package_name-versions that are to be activated
    and some of the options that can be passed on the command-line.
    """
    # Iterate through the list of package_name-versions and for each project,
    # ensure that the appropriate version for that project is activated.
    local = get_site_packages()
    for project in project_list:
        (project_name, project_version) = parse_project_str(project)
        try:
            pkgs = local.projects[project_name].packages
        except KeyError:
            # If we can't find a project key in the local.projects, that means that it was removed
            # from the system(not just deactivated), so we try to re-install it.
            req_str = "%s==%s" % (project_name, project_version)
            requirement = Requirement.parse(req_str)
            if project_name.endswith('.dev') and project_version.startswith('r'):
                # If we found a package that was installed by a 'setup.py develop', try to activate
                # it by finding it's location ignoring the specific revision number, since we can't
                # control if someone has done an 'svn up' on their checkouts.
                name = project_name.split('-')[0]
                pkgs = local.projects[name].packages
            else:
                install_requirement([requirement], remote_repos=remote_repos,
                    interactive=interactive, dry_run=dry_run,
                    term_width=term_width)
        for pkg in pkgs:
            if pkg.version == project_version:
                pkg.activate(verbose=False)
                break
            if project_name.endswith('.dev') and project_version.startswith('r'):
                if '.dev-r' in pkg.version:
                    pkg.activate(verbose=False)
                    break
            
    # We also need to deactivate any packages that the user has installed since
    # the rollback point.
    active_local_packages = []
    for project in local.projects:
        pkg = local.projects[project].active_package
        if pkg:
            active_local_packages.append(pkg.project.name)
    for package in active_local_packages:
        new_package = True
        for project in project_list:
            if package in project:
                new_package = False
                break
        if new_package:
            pkg = local.projects[package].active_package
            pkg.deactivate(dry_run=False)
            
