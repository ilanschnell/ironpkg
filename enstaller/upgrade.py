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


def reason(reasons, project, message):
    reasons[project] = reasons.get(project, []) + [message]

def resolve_flexible(fixed, flexible, installed_flexible, installed, available,
                     reasoning):
    """Recursively resolve a set of dependencies.
    
    Parameters
    ----------
    fixed : a dictionary consisting of project keys and corresponding packages
            that have been decided upon in the current scenario
    flexible : a dictionary consisting of projects and a corresponding set of
            packages where we may have choice, but where we cannot use the
            currently installed package
    installed_flexible : a dictionary consisting of projects and a
            corresponding set of packages where we may have choice, and where
            the currently installed package is OK - the default is not to
            change anything
    installed : a dictionary representing the current state of the system
    available : a dictionary representing the available projects and their
            packages
    
    Return
    ------
    
    proposal : a dictionary of project keys and packages that represents the
            required changes
    reasons : a dictionary of project keys and reasons for the selection of
            each package
    
    Notes
    -----
    
    This function is in fact a generator, so if you don't need to have all
    possibilities generated, you can just grab the first one (which should be
    the most preferred).
    
    Algorithm
    ---------
    
    If there are no flexible projects, we have a consistent set in the fixed
    variable, so we can yield that.
    
    Otherwise, we chose one of the flexible projects, and for each possible
    choice, we look at what it depends on and what depends on it:
        * if these projects are fixed, we check that the current choice is
            satisfactory
        * if these projects are flexible or installed_flexible, we restrict
            the choices based on the requirements, possibly shifting
            installed_flexible projects if the currently installed option does
            not satisfy any more
        * other projects are added to flexible or installed_flexible as
            appropriate.
    If at any point the set of choices for flexible or installed_flexible
    projects is empty, or we conflict with a fixed project, we rule the package
    out, and proceed to the next one.
    
    If a package passes all the tests, then we make a recursive call and,
    presuming success, yield the results.
    
    When trying packages, the general strategy is that if we have to upgrade,
    then we should use the most up-to-date package that is compatible with the
    requirements.
    """
    #XXX We have a bug in this - it can loop forever or return duplicates.
    
    if flexible:
        # pick one
        project = list(flexible)[0]
        packages = flexible.pop(project)
        for package in sorted(packages, key=lambda p: p.distribution, reverse=True):
            new_fixed = fixed.copy()
            new_flexible = flexible.copy()
            new_installed_flexible = installed_flexible.copy()
            new_reasoning = reasoning.copy()
            new_fixed[project] = package
            new_reasoning[project] = ["".join(reasoning.get(project,[])) + \
                    "  Install version: " + package.version]
            package_ok = True
            for req in package.requires():
                if req.key in fixed:
                    if new_fixed[req.key].distribution not in req:
                        # failure: package requirement conflicts with fixed project
                        package_ok = False
                        break
                elif req.key in flexible:
                    new_flexible[req.key] = set(v for v in new_flexible[req.key]
                                            if v.distribution in req)
                    if not new_flexible[req.key]:
                        # failure: package requirement conflicts with flexible project
                        package_ok = False
                        reason(new_reasoning, req.key, "  - %s can't satisfy %s\n"
                               % (package.name, str(req)))
                        break
                elif req.key in new_installed_flexible:
                    if installed[req.key] in installed:
                        new_installed_flexible[req.key] = set(v
                                for v in new_installed_flexible[req.key]
                                if v.distribution in req)
                    else:
                        new_flexible[req.key] = set(v
                                for v in new_installed_flexible[req.key]
                                if v.distribution in req)
                        del new_installed[req.key]
                        if not new_flexible[req.key]:
                            # failure: package requirement conflicts with flexible project
                            package_ok = False
                            reason(new_reasoning, req.key, "  - %s can't satisfy %s\n"
                                   % (package.name, str(req)))
                            break
                elif req.key in installed:
                    if installed[req.key] in req:
                        new_installed_flexible[req.key] = set(v
                                for v in available[req.key].packages
                                if v.distribution in req)
                    else:
                        new_flexible[req.key] = set(v
                                for v in available[req.key].packages
                                if v.distribution in req)
                        if not new_flexible[req.key]:
                            # failure: package requirement conflicts with flexible project
                            package_ok = False
                            reason(new_reasoning, req.key, "  - %s can't satisfy %s\n"
                                   % (package.name, str(req)))
                            break
                else:
                    if req.key in available:
                        new_flexible[req.key] = set(v
                                for v in available[req.key].packages
                                if v.distribution in req)
                    else:
                        package_ok = False
                        reason(new_reasoning, req.key, "  - can't find" +
                            " project %s to satisfy %s\n" % (req.key, str(req)))
                        break
                    if not new_flexible[req.key]:
                        # failure: package requirement conflicts with flexible project
                        package_ok = False
                        reason(new_reasoning, req.key, "  - %s can't satisfy %s\n"
                               % (package.name, str(req)))
                        break
                reason(new_reasoning, req.key, "  - %s requires %s\n" %
                       (package.name, str(req)))
            if not package_ok:
                continue
            
            # package satisfies all requirements
            active_projects = dict((key, pkg.project)
                                   for key, pkg in installed.items())
            for reversed_reqs_key, reversed_reqs_packages in \
                    package.reversed_reqs(active_projects).items():
                if reversed_reqs_key in installed:
                    if reversed_reqs_key in new_fixed:
                        if new_fixed[reversed_reqs_key] not in reversed_reqs_packages:
                            # failure: package reversed requirement conflicts with fixed project
                            package_ok = False
                            reason(new_reasoning, reversed_reqs_key,
                                   "  - %s fails to satisfy %s version(s) %s\n" %
                                   (package.name, reversed_reqs_key,
                                    ", ".join(pkg.version for pkg in reversed_reqs_packages)))
                            break
                    elif reversed_reqs_key in new_flexible:
                        new_flexible[reversed_reqs_key] = \
                                new_flexible[reversed_reqs_key].intersection(reversed_reqs_packages)
                        if not new_flexible[reversed_reqs_key]:
                            # failure: package reversed requirement conflicts with flexible project
                            package_ok = False
                            reason(new_reasoning, reversed_reqs_key,
                                   "  - %s fails to satisfy %s version(s) %s\n" %
                                   (package.name, reversed_reqs_key,
                                    ", ".join(pkg.version for pkg in reversed_reqs_packages)))
                            break
                    elif reversed_reqs_key in new_installed_flexible:
                        possible = new_installed_flexible[reversed_reqs_key].intersection(reversed_reqs_packages)
                        if installed[reversed_reqs_key] in possible:
                            new_installed_flexible[reversed_reqs_key] = possible
                        else:
                            new_flexible[reversed_reqs_key] = possible                            
                    else:
                        if installed[reversed_reqs_key] in reversed_reqs_packages:
                            new_installed_flexible[reversed_reqs_key] = \
                                    set(reversed_reqs_packages)
                        else:
                            new_flexible[reversed_reqs_key] = \
                                    set(reversed_reqs_packages)                            
                        
                    reason(new_reasoning, reversed_reqs_key,
                           "  - %s satisfies requirements of %s version(s) %s\n" %
                           (package.name, reversed_reqs_key,
                            ", ".join(pkg.version for pkg in reversed_reqs_packages)))
            if not package_ok:
                continue
            
            for result in resolve_flexible(new_fixed, new_flexible,
                                           new_installed_flexible, installed,
                                           available, new_reasoning):
                yield result
    else:
        # if there are no flexible packages, then the fixed packages are a consistent
        # set of projects
        yield fixed, reasoning
    
                
def upgrade(packages, installed, available):
    fixed = {}
    flexible = dict((pkg.key, set([pkg])) for pkg in packages)
    installed_flexible = {}
    return resolve_flexible(fixed, flexible,
                    installed_flexible, installed, available, {})
                