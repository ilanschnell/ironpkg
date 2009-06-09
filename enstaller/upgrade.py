#------------------------------------------------------------------------------
# Copyright (c) 2008-2009, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#------------------------------------------------------------------------------

from pkg_resources import compose_version_string, parse_version



def get_upgrade_str(name, version, upgrade=True):
    """
    Return a requirement string that defines an upgrade to a project spec.

    Given a package name and version, return a requirement string in
    pkg_resources.Requirement format that can be used to retrieve
    an upgrade to that particular package version.  By default,
    the string returned would be an upgrade (i.e. change in major version)
    but if 'upgrade' is set to False, it will return a string
    that would constitute an update (i.e. change in minor or patch version.)
    """

    # FIXME: This is legacy code that probably isn't needed anymore.
    # Strip off any of Enthought's special tags representing distributions
    # with post-install scripts.
    orig_version = version
    if version[-2:] == "-s":
        version = version[:-2]

    # Find out the length of the version string as split by '.' and the length
    # of what we consider the major part of the version.
    version_len = len(version.split('.'))
    major_len = len(version.split('.')) // 2

    # Retrieve the version_parts from pkg_resources.parse_version.
    # Separate the major part from the version_parts, which signifies the
    # difference between the parts of the version that represent major/minor
    # level upgrades and patch/build level updates.
    version_parts = parse_version(version)
    major_part = version_parts[:major_len]

    # Special case to handle when there is only a single version part.
    # In this case, only an upgrade can be performed because each version must
    # have at least 1 major version number.  However, if this single version is
    # a mix of integers and characters, then we can determine an upgrade/update
    # based on that.
    if version_len == 1:
        if len(version_parts) == 2:
            if upgrade:
                req_str = "%s>%s" % (name, orig_version)
            else:
                req_str = "%s==%s" % (name, orig_version)
        else:
            upgrade_version = str(int(version_parts[0])+1)
            if upgrade:
                req_str = "%s>=%s" % (name, upgrade_version)
            else:
                req_str = "%s>%s, <%s" % (name, orig_version, upgrade_version)
        return req_str

    # Retrieve the last entry of the major part so that we can increment it to
    # determine our upgrade version number.  Convert the end of the major part
    # to an integer or it's ASCII code and then increment it and convert it
    # back to a string to be placed back in the major part of the version.
    end_part = major_part[-1]
    try:
        end_part = int(end_part)
    except:
        end_part = ord(end_part[-1])
    end_part = str(end_part+1)

    # If there is only one item in the major_part tuple, then the upgrade
    # version is just the end_part, which is the major_part incremented.
    # Otherwise, we need to convert the major_part tuple into a list so that we
    # can remove its last entry and then append our incremented end_part and
    # retrieve an upgrade version from that.
    if len(major_part) == 1:
        upgrade_version = end_part
    else:
        major_parts = list(major_part[:-1])
        major_parts.append(end_part)
        major_parts = tuple(major_parts)
        upgrade_version = compose_version_string(major_parts)

    # Calculate the requirement string based on whether we are doing an upgrade
    # or an update.
    if upgrade:
        req_str = "%s>=%s" % (name, upgrade_version)
    else:
        req_str = "%s>%s, <%s" % (name, orig_version, upgrade_version)

    return req_str


def reason(reasons, project, message):
    reasons[project] = reasons.get(project, []) + [message]


def resolve_flexible(fixed, flexible, installed_flexible, installed, available,
    reasoning):
    """
    Recursively resolve a set of dependencies.

    Parameters
    ----------
    fixed : a dictionary consisting of project keys and corresponding
        distributions that have been decided upon in the current scenario.
    flexible : a dictionary consisting of projects and a corresponding set of
        distributionss where we may have choice, but where we cannot use the
        currently installed distribution.
    installed_flexible : a dictionary consisting of projects and a
        corresponding set of distributions where we may have choice, and where
        the currently installed distribution is OK - the default is not to
        change anything
    installed : a dictionary representing the current state of the system.
    available : a dictionary representing the available projects and their
        distributions.


    Return
    ------
    proposal : a dictionary of project keys and distributionss that represent
        the required changes
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
            installed_flexible projectss if the currently installed option does
            not satisfy any more
        * other projects are added to flexible or installed_flexible as
            appropriate.
    If at any point the set of choices for flexible or installed_flexible
    projects is empty, or we conflict with a fixed project, we rule the
    distribution out, and proceed to the next one.

    If a distribution passes all the tests, then we make a recursive call and,
    presuming success, yield the results.

    When trying distributions, the general strategy is that if we have to
    upgrade, then we should use the most up-to-date distribution that is
    compatible with the requirements.

    """
    # FIXME:  We have a bug in this - it can loop forever or return duplicates.

    if flexible:
        # pick one
        project = list(flexible)[0]
        packages = flexible.pop(project)
        for package in sorted(packages,
                              key=lambda p: p.distribution, reverse=True):
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
                        # failure: package requirement conflicts with fixed
                        #          project
                        package_ok = False
                        break

                elif req.key in flexible:
                    new_flexible[req.key] = set(v for v in new_flexible[req.key]
                                            if v.distribution in req)
                    if not new_flexible[req.key]:
                        # failure: package requirement conflicts with
                        #          flexible project
                        package_ok = False
                        reason(new_reasoning,
                               req.key, "  - %s can't satisfy %s\n"
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
                            # failure: package requirement conflicts with
                            #          flexible project
                            package_ok = False
                            reason(new_reasoning, req.key,
                                   "  - %s can't satisfy %s\n"
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
                            # failure: package requirement conflicts
                            #          with flexible project
                            package_ok = False
                            reason(new_reasoning, req.key,
                                   "  - %s can't satisfy %s\n"
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
                        # failure: package requirement conflicts with
                        #          flexible project
                        package_ok = False
                        reason(new_reasoning, req.key,
                               "  - %s can't satisfy %s\n"
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
                        if (new_fixed[reversed_reqs_key]
                            not in reversed_reqs_packages):
                            # failure: package reversed requirement conflicts
                            #          with fixed project
                            package_ok = False
                            reason(new_reasoning, reversed_reqs_key,
                                   "  - %s fails to satisfy %s version(s) %s\n"
                                   %
                                   (package.name, reversed_reqs_key,
                                    ", ".join(pkg.version for pkg
                                              in reversed_reqs_packages)))
                            break

                    elif reversed_reqs_key in new_flexible:
                        new_flexible[reversed_reqs_key] = \
                                new_flexible[reversed_reqs_key].intersection(
                                           reversed_reqs_packages)

                        if not new_flexible[reversed_reqs_key]:
                            # failure: package reversed requirement conflicts
                            #          with flexible project
                            package_ok = False
                            reason(new_reasoning, reversed_reqs_key,
                                   "  - %s fails to satisfy %s version(s) %s\n"
                                   %
                                   (package.name, reversed_reqs_key,
                                    ", ".join(pkg.version for pkg in
                                              reversed_reqs_packages)))
                            break

                    elif reversed_reqs_key in new_installed_flexible:
                        possible = new_installed_flexible[reversed_reqs_key].intersection(reversed_reqs_packages)
                        if installed[reversed_reqs_key] in possible:
                            new_installed_flexible[reversed_reqs_key] = possible
                        else:
                            new_flexible[reversed_reqs_key] = possible
                    else:
                        if (installed[reversed_reqs_key] in
                            reversed_reqs_packages):
                            new_installed_flexible[reversed_reqs_key] = \
                                    set(reversed_reqs_packages)
                        else:
                            new_flexible[reversed_reqs_key] = \
                                    set(reversed_reqs_packages)

                    reason(new_reasoning, reversed_reqs_key,
                        "  - %s satisfies requirements of %s version(s) %s\n" %
                        (package.name, reversed_reqs_key,
                         ", ".join(pkg.version
                                   for pkg in reversed_reqs_packages)))
            if not package_ok:
                continue

            for result in resolve_flexible(new_fixed, new_flexible,
                                           new_installed_flexible, installed,
                                           available, new_reasoning):
                yield result
    else:
        # if there are no flexible packages, then the fixed packages are a
        # consistent set of projects
        yield fixed, reasoning


def upgrade(packages, installed, available):
    fixed = {}
    flexible = dict((pkg.key, set([pkg])) for pkg in packages)
    installed_flexible = {}
    return resolve_flexible(fixed, flexible, installed_flexible, installed,
        available, {})
