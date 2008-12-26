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
from repository import EasyInstallRepository


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
        print ("The enstaller.cache does not exist so a rollback "
            "can not be done.")
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


def save_state():
    """
    Adds an entry of the current working configuration of packages to the
    enstaller.cache file.
    """
    # Determine the current local repository and from that build a list of the current
    # active packages.
    site_packages = sysconfig.get_python_lib()
    local = EasyInstallRepository(location=site_packages)
    active_local_packages = []
    for project in local.projects:
        pkg = local.projects[project].active_package
        if pkg:
            active_local_packages.append(pkg)
            
    # Retrieve a list of project_name-version for the currently active packages.
    project_list = []
    for pkg in active_local_packages:
        project_list.append("%s-%s" % (pkg.project.name, pkg.version))
        
    # Save the current state to an entry in the enstaller.cache file.  Each entry begins
    # with a timestamp, followed by a colon, and then a comma separated list of the
    # project_name-versions for the currently active packages.
    enstaller_cache = os.path.join(site_packages, 'enstaller.cache')
    timestamp = strftime("%Y%m%d%H%M%S")
    pkg_list = ','.join(project_list)
    try:
        f = open(enstaller_cache, 'a')
        f.write(timestamp + ':')
        f.write(pkg_list)
        f.write('\n')
        f.close()
    except:
        print "Error trying to write to the enstaller.cache."
    
    
def rollback_state(project_list):
    """
    Input is a list of package_name-versions that are to be activated.
    """
    # Iterate through the list of package_name-versions and for each project,
    # ensure that the appropriate version for that project is activated.
    # Note: We have to take into account that some of the projects have names like
    # foo-bar-1.2.3.  We also need to account for the post-install script flag.
    site_packages = sysconfig.get_python_lib()
    local = EasyInstallRepository(location=site_packages)
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
        try:
            pkgs = local.projects[project_name].packages
        except KeyError:
            # FIXME:  If we can't find a project key in the local.projects, we should
            # probably re-download it if possible.  For now, just skip the project.
            continue
        for pkg in pkgs:
            if pkg.version == project_version:
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
            