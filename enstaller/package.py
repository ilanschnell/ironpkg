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
import os
import subprocess
import urllib2
from logging import debug, info, warning
from shutil import rmtree, copyfile
import re
from glob import glob

# imports from 3rd party packages
from pkg_resources import Requirement, Distribution
from setuptools.package_index import distros_for_url, find_distributions, \
    ensure_directory, open_with_auth
from setuptools.archive_util import unpack_archive

# local imports
from utilities import rmtree_error, run_scripts, get_egg_specs_from_info

EGG_INFO_RE = re.compile(r".*EGG-INFO")

class Package(object):
    """A Package is a particular installable
    """
    
    active = False
    
    def __init__(self, project, version):
        self.project = project
        self.version = version
        self.parsed_version = parse_version(version)
    
    @property
    def repository(self):
        return self.project.repository
    
    @property
    def metadata(self):
        return {
            'project_name': self.project.name,
            'version': self.version
        }
    
    def match(self, combiner='and', **kwargs):
        if not kwargs: return True
        matches = []
        for key, value in kwargs:
            if isinstance(value, basestring):
                matches.append(self.metadata.get(key,'') == value)
            else:
                matches.append(value.match(self.metadata.get(key,'')))
        if combiner == 'or':
            return reduce(lambda x, y: x or y, matches, False)
        return reduce(lambda x, y: x and y, matches, True)

class PkgResourcesPackage(Package):
    """A PkgResourcesPackage is an installable wrapping a pkg_resources.Distribution
    object
    """
    
    inherited_metadata = ["location", "project_name", "key", "extras",
                          "version", "parsed_version", "py_version",
                          "platform", "precedence"]

    def __init__(self, project, distribution):
        self.project = project
        self.distribution = distribution
    
    @property
    def requirement(self):
        return Requirement.parse("%s == %s" % (self.project.name,
                                               self.version))
    
    @property
    def name(self):
        return "%s %s" % (self.distribution.project_name, self.distribution.version)
    
    @property
    def key(self):
        return self.distribution.key
    
    @property
    def location(self):
        return self.distribution.location
    
    @property
    def version(self):
        return self.distribution.version
    
    @property
    def parsed_version(self):
        return self.distribution.parsed_version
    
    @property
    def precedence(self):
        return self.distribution.precedence

    def reversed_reqs(self, active_projects):
        """ Find all local packages which depend on this package
        """
        projects = {}
        for key, project in active_projects.items():
            dependencies = set(package for package in project.packages
                               if package.depends_on(self))
            if dependencies:
                projects[key] = dependencies
        return projects

class EasyInstallPackage(PkgResourcesPackage):
    """An EasyInstallPackage represents a locally installed egg.
    """
    @property
    def metadata(self):
        metadata = dict([(attr, getattr(self.distribution, attr, None))
                      for attr in self.inherited_metadata])
        active_env = self.project.repository.active
        metadata['location'] = active_env.make_relative(self.distribution.location)
        if self.active:
            metadata['active'] = "Y"
        else:
            metadata['active'] = ""
        return metadata

    @property
    def active(self):
        return self.distribution in set(self.project.repository.active[self.project.name])
    
    def requires(self):
        return self.distribution.requires()
    
    def depends_on(self, package):
        """Does a given package depend on this package
        
        Parameters
        ----------
        package : a PkgResource package
        """
        matches = [package.distribution in requirement
                   for requirement in self.distribution.requires()]
        return reduce(lambda x,y: x or y, matches, False)
    
    @property
    def dependent_packages(self):
        """ Find active packages which immediately depend on this package
        """
        if self.active:
            return [package
                    for package in self.project.repository.active_packages
                    if package.depends_on(self)]
        else:
            return []
    
    @property
    def full_dependent_packages(self):
        """ Recursively find all active packages which depend on this package
        """
        if self.active:
            packages = set(self.dependent_packages)
            for package in self.dependent_packages:
                packages |= package.full_dependent_packages
            return packages
        else:
            return set()
            
    #@property
    #def reversed_reqs(self):
    #    """ Find all local packages which depend on this package
    #    """
    #    projects = {}
    #    for key, project in self.project.repository.projects.items():
    #        dependencies = set(package for package in project.packages
    #                           if package.depends_on(self))
    #        if dependencies:
    #            projects[key] = dependencies
    #    return projects
    
    def activate(self, save=True, dependencies=True, dry_run=False,
        verbose=True):
        """Activate the package, adding it to the Python import path.

        Parameters
        ----------
        save : boolean
            Should changes to the repository be saved now?
        dependencies : boolean
            Should we ensure a consistent state after activation?
        verbose : boolean
            Should all of the output be shown or just if something was
            changed(i.e. activated when it was deactivated)?
        """
        if not self.active:
            if self.project.active:
                self.project.deactivate(save=False, dependencies=False,
                                        dry_run=dry_run)
            info("Activating package %s..." % (self.name))
            if not dry_run:
                self.project.repository.active.add(self.distribution)
            else:
                print "Activate package %s" % self.name
            if save:
                if not dry_run:
                    self.repository.active.save()
                else:
                    print "Save .pth file."
            run_scripts(self.distribution, "post-activate", dry_run=dry_run)
        else:
            if verbose:
                warning("Package %s is already active." % (self.name))
    
    def deactivate(self, save=True, dependencies=False, dry_run=True):
        """Deactivate the package, removing it from the Python import path.
        
        Parameters
        ----------
        save : boolean
            Should changes to the repository be saved now?
        dependencies : boolean
            Should we ensure a consistent state by deactivating all packages
            which depend on this one?
        """
        if self.active:
            #if dependencies:
            #    for package in self.dependent_packages:
            #        package.deactivate(save=False, dependencies=True,
            #                           dry_run=dry_run)
            for package in sorted(self.full_dependent_packages,
                    key=lambda x: x.name):
                warning("Package %s depends upon %s and may no longer work correctly"
                    % (package.name, self.name))
            run_scripts(self.distribution, "pre-deactivate", dry_run=dry_run)
            info("Deactivating package %s..." % (self.name))
            if not dry_run:
                self.project.repository.active.remove(self.distribution)
            else:
                print "Deactivate package %s..." % (self.name)
            if save:
                if not dry_run:
                    self.repository.active.save()
                else:
                    print "Save .pth file."
        else:
            warning("Package %s is already inactive." % (self.name))
    
    def remove(self, dry_run=False):
        """ Uninstall the package, removing all files and attempting to
        restore to the pre-installed state.
        """
        # XXX we would like to replace most of this with a call out to
        # our patched version of setuptools.  For the time being I'm leaving
        # this in here, since we don't have the interface set yet.
        
        if self.active:
            # deactivate self and anything which depends on this package
            self.deactivate(dry_run=dry_run)
        run_scripts(self.distribution, "pre-uninstall", dry_run=dry_run)
        
        # XXX this isn't working properly, but I'm not going to fight it
        # since we're replacing this with patched setuptools
        
        # if we have a files file
        files_file = self.location + ".files"
        if os.path.exists(files_file):
            # extract the list of files
            fp = open(files_file)
            try:
                file_list = [filename.strip()
                             for filename in fp.read().split('\n')]
            finally:
                fp.close()    
            # and try to remove each file from the list
            for filename in file_list:
                if os.path.exists(filename):
                    if os.path.isdir(filename):
                        try:
                            os.rmdir(filename)
                        except Exception, exc:
                            rmtree_error(os.rmdir, filename, exc)
                    elif os.path.isfile(filename) or os.path.islink(filename):
                        try:
                            os.remove(filename)
                        except Exception, exc:
                            rmtree_error(os.remove, filename, exc)
        else:
            info("Could not find installed file list for '%s' at %s" %
                (self.name, files_file))
        # now remove the egg dir or file
        if os.path.exists(self.location):
            info("Removing egg at %s" % self.location)
            if os.path.isdir(self.location):
                # I think the best thing to do here is to blow away the whole
                # directory
                rmtree(self.location, onerror=rmtree_error)
            elif os.path.isfile(self.location) or os.path.islink(self.location):
                try:
                    os.remove(self.location)
                except:
                    rmtree_error(os.remove, self.location, sys.exec_info())
        else:
            warning("Egg not found.  Already removed?")
        # finally remove the files file
        if os.path.exists(files_file):
            try:
                os.remove(self.location)
            except:
                rmtree_error(os.remove, self.location, sys.exec_info())
       
    
class RemotePackage(PkgResourcesPackage): 
    """An RemotePackage represents an egg that can be installed from a remote
    repository.
    """
    def __init__(self, *args, **kwargs):
        super(RemotePackage, self).__init__(*args, **kwargs)
        self._local_dist = None
        self.source = False
        self.develop = False
    
    @property
    def tmpdir(self):
        return os.path.join(self.repository.tmpdir, self.project.name,
            self.version)
    
    @property
    def local_distribution(self):
        if self._local_dist is None:
            ensure_directory(os.path.join(self.tmpdir, "dummy"))
            info("Fetching %s from %s..." % (str(self.distribution),
                self.location))
            dist = self.repository.environment.fetch_distribution(self.requirement,
                self.tmpdir, source=self.source, develop_ok=self.develop)
            location = dist.location
            distros = list(find_distributions(location))
            if distros:
                self._local_dist = distros[0]
            elif os.path.isfile(location) and os.path.splitext(location) != \
                    ".py":
                # try to unpack the file
                unpack_dir = os.path.join(self.tmpdir, "unpack")
                info("Unpacking to %s..." % unpack_dir)
                unpack_archive(location, unpack_dir)
                distros = list(find_distributions(unpack_dir))
                if distros:
                    self._local_dist = distros[0]
                else:
                    for path in glob(os.path.join(unpack_dir, "*")):
                        distros = list(find_distributions(path))
                        if distros:
                            self._local_dist = distros[0]
                            break
                    else:
                        self._local_dist = Distribution.from_filename(location)
        return self._local_dist
    
    def requires(self):
        if self.metadata.has_key("depends"):
            print self.metadata["depends"]
            return self.metadata["depends"]
        return self.local_distribution.requires()
    
    def install(self, target_repo, source=False, develop=False, dry_run=False, *args):
        """Install a package by fetching it into a temporary directory and then
        calling easy_install with the appropriate args.
        """
        args = list(args)
        files_file = os.path.join(self.tmpdir, "files")
        #if "--location" not in args:
        #    args += ["--install-dir=%s" % target_repo.location]
        
        # XXX this option should become the default when we patch setuptools
        # wo we can remove these two lines
        if "--record" not in args:
            args += ["--record=%s" % files_file]
        if "--no-deps" not in args:
            args += ["--no-deps"]

        if not dry_run:
            location = self.local_distribution.location
        else:
            print "Download egg file to temporary directory"
        
        # XXX more sophistication here?
        info("Installing %s" % str(self.distribution))
        if not dry_run:
            subprocess.call(["easy_install"] + args + [location])
        else:
            print "Execute", " ".join(["easy_install"] + args + ["<location>"])
            
        # want to copy the files file
        # XXX Don't worry about this when we start to use patched setuptools
        if not dry_run:
            f = open(files_file)
            try:
                files = f.read().split('\n')
            finally:
                f.close()
            for file in files:
                match = EGG_INFO_RE.match(file)
                if match:
                    dir = match.group(0)
                    break
            else:
                # can't find the EGG-INFO dir
                return
            base, egg_info = os.path.split(dir)
            new_files = os.path.join(base, ".files")
            copyfile(files_file, new_files)
        else:
            print "Copy the list of installed files to the install location."

        if not dry_run:
            dist = Distribution.from_filename(base)
            run_scripts(dist, "post-install", dry_run=dry_run)
            # XXX would really like to have a separate activation step, but
            # setuptools automatically activates in install
            run_scripts(dist, "post-activate", dry_run=dry_run)
        else:
            print "Run post-install scripts."
            print "Run post-activate scripts."

class HTMLPackage(RemotePackage):
    """An RemotePackage represents an egg that can be installed from a remote
    HTML-style repository.
    """
    @property
    def metadata(self):
        metadata = dict([(attr, getattr(self.distribution, attr, None))
                      for attr in self.inherited_metadata])
        metadata['active'] = ""
        
        # is there an .egg.info metadata file?
        # XXX if we're going to patch setuptools, we might want to simply have
        # setuptools do this when it creates a Distribution for this in
        # package_index
        if self.location.endswith(".egg"):
            egg_info_url = self.location +".info"
        else:
            egg_info_url = self.location +".egg.info"
        try:
            url = open_with_auth(egg_info_url)
            egg_info = get_egg_specs_from_info(url.read())
            metadata.update(egg_info)
        except urllib2.URLError:
            info("No .egg.info link available for %s" % self.name)
            
        return metadata


class XMLRPCPackage(RemotePackage):
    """An RemotePackage represents an egg that can be installed from a remote
    PyPI-style XMLRPC repository.
    """
    @property
    def metadata(self):
        if self._metadata == None:
            self._metadata = self.project.repository.server.release_data(
                    self.project.name, self.version)
        metadata['active'] = ""
        
        # is there an .egg.info metadata file?
        if self.location.endswith(".egg"):
            egg_info_url = self.location +".info"
        else:
            egg_info_url = self.location +".egg.info"
        try:
            url = open_with_auth(egg_info_url)
            egg_info = get_egg_specs_from_info(url.read())
            metadata.update(egg_info)
        except urllib2.URLError:
            info("No .egg.info link available for %s" % self.name)
        
        return self._metadata
