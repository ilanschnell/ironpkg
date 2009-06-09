#------------------------------------------------------------------------------
# Copyright (c) 2008-2009 by Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license
# available at http://www.enthought.com/licenses/BSD.txt and may be
# redistributed only under the conditions described in the aforementioned
# license.
#------------------------------------------------------------------------------

import os
from shutil import rmtree
from tempfile import mkdtemp
from xmlrpclib import Server
from distutils.errors import DistutilsError
from os.path import abspath, exists, isdir

from enstaller.project import (Project, ProjectUnion, PkgResourcesProject,
                               EasyInstallProject, HTMLProject, XMLRPCProject)
from enstaller.utilities import rst_table, rmtree_error
from logging import debug, info, warning
from pkg_resources import Environment
from setuptools.command.easy_install import PthDistributions
from setuptools.package_index import PackageIndex, URL_SCHEME


class Repository(object):
    """\
    A repository represents a collection of projects which contain packages.

    """

    default_package_fields = ["project_name", "version", "location"]

    def __init__(self, location, verbose=False):
        self.location = location
        self.verbose = verbose

    def build_package_list(self):
        for project in self.projects.values():
            project.packages

    def pretty_packages(self, fields=None, max_width=0):
        if fields == None:
            fields = self.default_package_fields
        return rst_table(fields,
                         [package.metadata for package in self.packages],
                         max_width=max_width)

    @property
    def packages(self):
        packages = []
        for project in sorted(self.projects):
            packages += self.projects[project].packages
        return packages

    def __getitem__(self, key):
        return self.projects[key]

    def __setitem__(self, key, value):
        self.projects[key] = value

    def __delitem__(self, key):
        del self.projects[key]

    def __contains__(self, key):
        if isinstance(key, basestring):
            return key in self.projects


class RepositoryUnion(Repository):
    """\
    A union of several repositories that acts as a single repository.

    """

    def __init__(self, repositories, verbose=False):
        # NOTE: Explicitly not calling the base class constructor.  We
        # don't have all the same attributes.
        self.repositories = repositories
        self._projects = None
        self.verbose = verbose

    @property
    def projects(self):
        if not self._projects:
            projects = {}
            for repo in self.repositories:
                for key, project in repo.projects.items():
                    if key in projects:
                        projects[key].projects.append(project)
                    else:
                        projects[key] = ProjectUnion(self, key, [project])
            self._projects = projects
        return self._projects


class LocalRepository(Repository):
    """\
    A local repository is a repository on the host machine.

    """

    def search(self, combiner='and', **kwargs):
        matches = []
        for project in self.projects:
            matches += self.projects[project].search(combiner, **kwargs)
        return matches


class EasyInstallRepository(LocalRepository):
    """\
    A local repository which is controlled by an easy_install.pth file.

    """
    _pth = "easy-install.pth"
    default_package_fields = ["project_name", "version", "active", "location"]

    def __init__(self, location, verbose=False):
        self._projects = None
        self.location = location
        self._pth_file = os.path.join(self.location, self._pth)
        self.environment = Environment(search_path=[self.location])
        self.active = PthDistributions(self._pth_file)
        self.verbose = verbose


    @property
    def projects(self):
        if self._projects == None:
            self._projects = {}
            for key in self.environment:
                self._projects[key] = EasyInstallProject(self, key)
        return self._projects

    @property
    def active_packages(self):
        packages = []
        for project in self.projects.values():
            for package in project.packages:
                if package.active:
                    packages.append(package)
        return packages


class RemoteRepository(Repository):
    def __init__(self, *args, **kwargs):
        super(RemoteRepository, self).__init__(*args, **kwargs)
        self.tmpdir = mkdtemp(prefix="enstaller-")

    def __del__(self):
        rmtree(self.tmpdir, onerror=rmtree_error)


def format_as_url(location):
    """
    Return a url-formatted version of the location.

    If the location doesn't already have a URL scheme as a prefix, we
    assume it is a path on the local filesystem.

    """
    if URL_SCHEME(location):
        return location

    # Ensure any file or directory path actually exists.
    if not exists(location):
        raise DistutilsError('Location does not exist: %s' % location)

    # If it is a directory, make sure it ends with a trailing slash -- because
    # package_index functions expect it that way.
    location = abspath(location)
    if isdir(location) and not location.endswith('/'):
        location = location + '/'

    return 'file://' + location


class HTMLRepository(RemoteRepository):
    """\
    A remote repository which easy_install can cope with.

    """
    def __init__(self, location, index=False, verbose=False):
        self.location = format_as_url(location)
        self.index = index
        if index:
            self.environment = PackageIndex(index_url=self.location,
                                            search_path=[])
        else:
            self.environment = PackageIndex(no_default_index=True)
            self.environment.add_find_links([self.location])
        self._projects = None
        self.tmpdir = mkdtemp(prefix="enstaller-")
        self.verbose = verbose

    @property
    def projects(self):
        if self._projects == None:
            self._projects = {}
            info("Scanning repository at %s..." % self.location)
            self.environment.prescan()
            self.environment.scan_all()
            for project in self.environment:
                self._projects[project] = HTMLProject(self, project,
                    verbose=self.verbose)
            for project in self.environment.package_pages:
                if project not in self._projects:
                    self._projects[project] = HTMLProject(self, project,
                        verbose=self.verbose)
                self._projects[project].scan_needed = True
        return self._projects

    def search(self, combiner='and', **kwargs):
        if 'project' not in kwargs:
            raise SearchError("EasyInstall-based remote repositories require"
                              " a 'project' search term.")
        if isinstance(kwargs['project'], basestring):
            return self.projects[kwargs['project']].match(combiner, **kwargs)
        partial_match_names = set(project_name
                                  for project_name in self.projects
                                  if kwargs['project'].match(project_name))
        matches = []
        for project in partial_match_names:
            matches += self.projects[project].search(combiner, **kwargs)
        return matches


class XMLRPCRepository(RemoteRepository):
    def __init__(self, location, verbose=False):
        self.location = location
        # an empty Environment to help with tracking packages
        self.environment = Environment(search_path=[])
        self.server = Server(self.location)
        self._projects = None
        self.tmpdir = mkdtemp(prefix="enstaller-")
        self.verbose = verbose

    @property
    def projects(self):
        if self._projects == None:
            info("Scanning repository at %s..." % self.location)
            for project in self.server.list_packages():
                self._projects[project] = XMLRPCProject(self, project)
        return self._projects

    def search(self, combiner='and', **kwargs):
        precise_terms = dict((key, value) for key, value in kwargs
                             if isinstance(value, basestring))
        if precise_terms:
            partial_match_names = set(partial_match['name']
                                      for partial_match in
                                      self.server.search(precise_terms,
                                                         combiner))
        else:
            partial_match_names = set(self.projects)
        matches = []
        for project in partial_match_names:
            matches += self.projects[project].search(combiner, **kwargs)
        return matches
