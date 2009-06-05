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

# imports from standard library
from logging import debug, info, warning
from tempfile import mkdtemp
from shutil import rmtree

# imports from 3rd party packages
from pkg_resources import Requirement

# local imports
from package import Package, PkgResourcesPackage, EasyInstallPackage, \
        HTMLPackage, XMLRPCPackage
from utilities import rst_table

class Project(object):
    """A Project represents a collection of different versions of an installable
    """
    active_package = None
    active = False
    
    def __init__(self, repository, name, verbose=False):
        self.repository = repository
        self.name = name
        self._packages = None
        self.verbose = verbose

    def search(self, combiner='and', **kwargs):
        return [package for package in self.packages
                if package.match(combiner, **kwargs)]
    
    def current_version(self):
        return self.packages[0]
    
    def pretty_packages(self, fields=None):
        if fields == None:
            fields = ["version", "location"]
        return rst_table(fields, [package.metadata for package in self.packages])

class ProjectUnion(Project):
    def __init__(self, repository, name, projects, verbose=False):
        super(ProjectUnion, self).__init__(repository, name, verbose=verbose)
        self.projects = projects
    
    @property
    def active(self):
        active = False
        for project in self.projects:
            active = active or project.active
        return active
    
    @property
    def active_package(self):
        for project in self.projects:
            if project.active:
                return project.active_package
        else:
            return None
    
    @property
    def packages(self):
        if self._packages == None:
            packages = []
            for project in self.projects:
                packages += project.packages
            self._packages = packages
        return self._packages

class PkgResourcesProject(Project):
    """A PkgResourcesProject is a project managed using the pkg_resource module
    """
    @property
    def packages(self):
        if self._packages == None:
            self._packages = []
            for dist in self.repository.environment[self.name]:
                self._packages.append(self.PackageType(self, dist))
        return self._packages
    
    @property
    def requirement(self):
        return Requirement.parse(self.name)
    
    @property
    def environment(self):
        return self.repository.environment

class EasyInstallProject(PkgResourcesProject):
    """An EasyInstallProject is a local project managed by the pkg_resource and
    easy_install.
    """
    PackageType = EasyInstallPackage
    
    @property
    def active(self):
        return self.name in set(self.repository.active)
    
    @property
    def active_package(self):
        active_packages = [package for package in self.packages
                           if package.active]
        if not active_packages:
            return None
        if len(active_packages) == 1:
            return active_packages[0]
        else:
            raise RepositoryConsistencyError("Project %s has multiple active "
                    "packages: " + ", ".join(package.version for package in active_packages))
   
    def activate(self, save=True):
        if not self.active:
            # add the most preferred package currently available
            info("Activating project %s..." % (self.name))
            self.packages[0].activate(save=save)
        else:
            warn("Project %s is already active." % (self.name))
    
    def deactivate(self, save=True, dependencies=True, dry_run=False):
        if self.active:
            for package in self.packages:
                if package.active:
                    package.deactivate(save=False, dependencies=dependencies,
                                       dry_run=dry_run)
            if save:
                self.repository.active.save()
        else:
            warn("Project %s is already inactive." % (self.name))
    
class RemoteProject(PkgResourcesProject):
    """An RemoteProject is a project located in a remote repository.
    """
    
    def fetch(self, tmpdir, source=False, develop=False):
        info("Fetching %s from %s..." % (self.name, self.repository.location))
        dist = self.repository.environment.fetch_distribution(self.requirement,
                tmpdir, source=source, develop_ok=develop)
        return dist.location
    
    def install(self, *args):
        """Install a package by fetching it into a temporary directory and then
        calling easy_install with the appropriate args.
        """
        tmpdir = mkdtemp(prefix="enstaller-")
        try:
            location = self.fetch(tmpdir, source, develop)
            # XXX more sophistication here?
            info("Installing %s" % self.name)
            sys.command(["easy_install", location] + args)
        finally:
            # remove the tmpdir
            rmtree(tmpdir)


class HTMLProject(RemoteProject):
    """An RemoteProject is a remote project located in a HTML-based repository.
    """

    PackageType = HTMLPackage
    
    def __init__(self, repository, name, verbose=False):
        # FIXME: Are we really purposefully avoiding calling the base class's
        # __init__ method?   Why??
        self.repository = repository
        self.name = name
        self._packages = None
        self.scan_needed = False
        self.verbose= verbose

    @property
    def packages(self):
        if self._packages == None:
            self._packages = []

            # load this package into the environment
            if self.name not in set(self.repository.environment) or \
                self.scan_needed:
                if self.verbose:
                    info("Finding distributions for project %s" % self.name)
                self.repository.environment.find_packages(self.requirement)

            for package in self.repository.environment[self.name]:
                self._packages.append(self.PackageType(self, package))

        return self._packages


class XMLRPCProject(RemoteProject):
    """An XMLRPCProject is a remote project located in a PyPI-style
    XMLRPC-based repository.
    """
    
    @property
    def packages(self):
        if self._packages == None:
            # find distributions in the repository
            distributions = []
            if self.verbose:
                info("Finding distributions for project %s" % self.name)
            for version in self.repository.server.package_releases(self.name):
                releases = self.repository.server.release_urls(self.name,
                                                               version)
                distributions += [distros_from_url(release['url'])
                                  for release in releases]
                if not releases:
                    info("  XMLRPC server returns no urls for %s version %s."
                         % (self.name, version))
                    metadata = self.repository.server.release_data(self.name,
                                                                   version)
                    info("Searching project download page '%s' for packages..."
                         % metadata['downloads'])
                    distributions += find_eggs_in_url(metadata['downloads'])
            for dist in distributions:
                self.repository.environment.add(dist)
            
            # find the distributions which match - there will likely be some
            # spurious distributions added by find_eggs_in_url() and
            # distros_from_url()
            self._packages = []
            for package in self.repository.environment[self.name]:
                self._packages.append(self.XMLRPCPackage(self, package.version, package))
        return self._packages

