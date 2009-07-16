# -*- coding: utf8 -*-
""" PEP 376
"""
from __future__ import with_statement
import os
from os.path import join, splitext, isdir
from os import listdir
from string import maketrans
import csv
import sys
import re
import threading
from zipfile import is_zipfile, ZipFile

from distutils.dist  import  DistributionMetadata
from distutils.errors import DistutilsError

SEP_TRANS = maketrans('/', os.path.sep)
SPACE_TRANS = maketrans(' ', '.')
DASH_TRANS = maketrans('-', '_')


#
# Utilities
#

def egginfo_dirname(name, version):
    """Returns the egg-info directory name of a project.

    ``name`` is converted to a standard distribution name any runs of
    non-alphanumeric characters are replaced with a single '-'. ``version``
    is converted to a standard version string. Spaces become dots, and all other
    non-alphanumeric characters become dashes, with runs of multiple dashes
    condensed to a single dash. Both attributes are then converted into their
    filename-escaped form. Any '-' characters are currently replaced with '_'.
    """
    name = re.sub('[^A-Za-z0-9.]+', '_', name)
    version = version.translate(SPACE_TRANS)
    version = re.sub('[^A-Za-z0-9.]+', '_', version)
    return '%s-%s.egg-info' % (name.translate(DASH_TRANS),
                               version.translate(DASH_TRANS))

#
# distutils.dist.DistributionMetadata new version
#
class _DistributionMetadata(DistributionMetadata):
    """distutils.dist.DistributionMetadata new version

    That can load an existing PKG-INFO file
    """
    def __init__ (self, file=None):
        if file is not None:
            self.read_pkg_file(file)
        else:
            self.name = None
            self.version = None
            self.author = None
            self.author_email = None
            self.maintainer = None
            self.maintainer_email = None
            self.url = None
            self.license = None
            self.description = None
            self.long_description = None
            self.keywords = None
            self.platforms = None
            self.classifiers = None
            self.download_url = None
            # PEP 314
            self.provides = None
            self.requires = None
            self.obsoletes = None

    def read_pkg_file(self, file):
        """Reads from a PKG-INFO file object and initialize the instance.
        """
        if isinstance(file, str):
            file = open(file, 'rU')

        pkg_info = file.read()
        re_options = re.I|re.DOTALL|re.M

        def _extract(fieldname):
            if fieldname == 'Description':
                # crappy, need to be reworked
                pattern = r'^Description: (.*)'
                res = re.findall(pattern, pkg_info , re_options)
                if len(res) == 0:
                    return 'UNKNOWN'
                else:
                    res = res[0].split('\n' + 8*' ')
                    res = [r for r in res if not r.startswith('\n')]
                    return '\n'.join(res) + '\n'

            pattern = r'^%s: (.*?)$' % fieldname
            res = re.findall(pattern, pkg_info , re_options)
            if fieldname in ('Classifier', 'Requires', 'Provides',
                             'Obsoletes'):
                return res
            if len(res) == 0:
                return 'UNKNOWN'
            return res[0]

        version = _extract('Metadata-Version')
        self.name = _extract('Name')
        self.version = _extract('Version')
        self.summary = _extract('Summary')
        self.url = _extract('Home-page')
        self.author = _extract('Author')
        self.author_email = _extract('Author-email')
        self.license = _extract('License')
        self.download_url = _extract('Download-URL')
        self.long_description = _extract('Description')
        self.keywords = _extract('Keywords').split(',')
        self.classifiers = _extract('Classifier')
        self.platform = _extract('Platform')

        # PEP 314
        if version == '1.1':
            self.requires = _extract('Requires')
            self.provides = _extract('Provides')
            self.obsoletes = _extract('Obsoletes')
        else:
            self.requires = None
            self.provides = None
            self.obsoletes = None


#
# function used to detect a PEP 376 .egg-info directory
#
def is_egginfo(path):
    """Returns True if `path` is an egg-info directory.

    Also makes sure it doesn't pick older versions by checking
    the presence of `RECORD` and `PKG-INFO`.
    """
    if not (splitext(path)[-1].lower() == '.egg-info' and isdir(path)):
        return False
    content = os.listdir(path)
    return 'PKG-INFO' in content and 'RECORD' in content


#
# Distribution class (with DistributionMetadata in it)
#
class Distribution(object):

    def __init__(self, path):
        self.path = path
        self.container, self.info_path = os.path.split(path)
        self.pkg_info_path = join(path, 'PKG-INFO')
        self.record_path = join(path, 'RECORD')
        pkginfo = self._open_pkginfo()
        self.metadata = _DistributionMetadata(pkginfo)
        self.name = self.metadata.name
        self._files = None

    def __str__(self):
        return "Distribution('%s')" % self.name

    def _load_record(self):
        """Loads the RECORD file."""
        if self._files is None:
            self._files = self._read_record()

    def _open_pkginfo(self):
        return open(self.pkg_info_path)

    def _open_record(self):
        return open(self.record_path)

    def _open_file(self, file, mode):
        return open(file, mode)

    def _read_record(self):
        """Reads RECORD."""
        files = []
        for row in csv.reader(self._open_record()):
            if row == []:
                continue
            location = row[0]
            md5 = len(row) > 1 and row[1] or None
            size = len(row) > 2 and row[2] or None
            files.append((location, md5, size ))
        return files

    def _local_path(self, path):
        """Transforms a '/'-separated path to an absolute path,
        using the local separator."""
        path = path.translate(SEP_TRANS)
        if path[0] == '/':
            return path
        return join(self.container, path)

    def get_installed_files(self, local=False):
        """Iterates over the RECORD entries.

        Returns a (location, md5, size) tuple.
        If local is True, translates the cross-platform path for each
        path into a local absolute path.
        """
        self._load_record()   # initializes self._files

        for location, md5, size  in self._files:
            if local:
                location = self._local_path(location)
            yield location, md5, size

    def get_egginfo_files(self, local=False):
        """Iterates over the list of files located in the `.egg-info`
        directory.

        If local is True, translates the cross-platform path for each
        path into a local absolute path.
        """
        self._load_record()  # initializes self._files
        for location, md5, size  in self._files:
            local_path = self._local_path(location)
            if not local_path.startswith(self.path):
                continue
            # the file is located under self.path
            if local:
                yield local_path
            else:
                yield location

    def uses(self, path):
        """Returns True if the path is listed in the RECORD file.

        e.g. if the project uses this file.
        """
        local = os.path.exists(path)
        for location, md5, size in self.get_installed_files(local):
            if location == path:
                return True
        return False

    def get_egginfo_file(self, path, binary=False):
        """Returns a file instance on the path.

        If binary is True, opens the file in binary mode.
        """
        path = path.translate(SEP_TRANS)
        if path[0] != '/':
            local_path = join(self.path, path)
        else:
            local_path = join(self.container, path)

            if not local_path.startswith(self.path):
                raise DistutilsError('%s is not located in %s' % \
                                     (path, self.path))
        return self._open_file(local_path, binary and 'rb' or 'r')

class ZippedDistribution(Distribution):

    def __init__(self, zipfile, path):
        self.zipfile = zipfile
        super(ZippedDistribution, self).__init__(path)
        self.container = self.zipfile.filename
        self.path = join(self.zipfile.filename, path)

    def _open_pkginfo(self):
        return self.zipfile.open(self.pkg_info_path)

    def _open_record(self):
        return self.zipfile.open(self.record_path)

    def _open_file(self, path, mode):
        if path.startswith(self.container):
            path = path[len(self.container)+1:]
        return self.zipfile.open(path, mode)

#
# DistributionDir represents a directory that contains egg-info files
#
class DistributionDir(set):

    def __init__(self, path):
        super(DistributionDir, self).__init__()
        self.path = path
        # filling the list once (see if it's the best way)
        # to minimize I/O
        for element in os.listdir(self.path):
            fullpath = join(self.path, element)
            if is_egginfo(fullpath):
                self.add(Distribution(fullpath))

    def __repr__(self):
        return 'DistributionDir("%s")' % self.path

    def add(self, dist):
        """Makes sure only Distribution instances are added."""
        if not isinstance(dist, Distribution):
            raise TypeError('DistributionDir manage only Distribution '
                            'instances')
        super(DistributionDir, self).add(dist)

    #
    # public APIs
    #
    def get_file_users(self, path):
        """Returns Distribution instances for the projects that uses `path`."""
        for dist in self:
            if dist.uses(path):
                yield dist


class ZippedDistributionDir(DistributionDir):

    def __init__(self, path):
        if not is_zipfile(path):
            raise TypeError('%s path is not a zipfile' % path)
        self.path = path
        self._zip_file = ZipFile(path)
        # scanning the zip content
        egg_infos = []
        for element in self._zip_file.filelist:
            paths = os.path.split(element.filename)
            if len(paths) < 2:
                continue
            if splitext(paths[0])[-1].lower() == '.egg-info':
                if paths[0] not in egg_infos:
                    self.add(ZippedDistribution(self._zip_file, paths[0]))
                    egg_infos.append(paths[0])

    def __repr__(self):
        return 'ZippedDistributionDir("%s")' % self.path

    def add(self, dist):
        """Makes sure only Distribution instances are added."""
        if not isinstance(dist, ZippedDistribution):
            raise TypeError('ZippedDistributionDir manage only '
                            'ZippedDistribution instances')
        super(ZippedDistributionDir, self).add(dist)


#
# Directories is a collection of directories, initialized with a
# list of paths.
#

_CACHED_DIRS = {}

def purge_cache():
    _CACHED_DIRS.clear()


class DistributionDirMap(dict):

    def __init__(self, paths=None, use_cache=True):
        super(DistributionDirMap, self).__init__()
        if paths is not None:
            self.load(*paths)
        self.use_cache = use_cache

    def __setitem__(self, path, dir):
        """Controls the mapping deals only with path/DistributionDir"""
        if not isinstance(path, str):
            raise TypeError('The key needs to be a path')
        if not isinstance(dir, (ZippedDistributionDir,
                                DistributionDir)):
            raise TypeError('The value needs to be a DistributionDir '
                            'or a ZippedDistributionDir instance')
        super(DistributionDirMap, self).__setitem__(path, dir)

    #
    # public APIs
    #
    def load(self, *paths):
        """Loads the paths."""
        for path in paths:
            if path in self or not (os.path.isdir(path) or
                                    is_zipfile(path)):
                continue
            if self.use_cache and path in _CACHED_DIRS:
                dist_dir = _CACHED_DIRS[path]
            else:
                if is_zipfile(path):
                    dist_dir = ZippedDistributionDir(path)
                else:
                    dist_dir = DistributionDir(path)
                if self.use_cache:
                    _CACHED_DIRS[path] = dist_dir

            self[path] = dist_dir

    def reload(self):
        """Reload all the paths."""
        paths = self.keys()
        self.clear()
        self.load(*paths)

    def get_distributions(self):
        """Returns an iterator over contained Distribution instances."""
        for directory in self.values():
            for dist in directory:
                yield dist

    def get_distribution(self, project_name):
        """Returns an Distribution instance for the given project name.

        If not found, returns None.
        """
        for directory in self.values():
            for dist in directory:
                if dist.name == project_name:
                    return dist

    def get_file_users(self, path):
        """Iterates over all projects to find out which project uses the file.

        Return Distribution instances.
        """
        for directory in self.values():
            for dist in directory.get_file_users(path):
                yield dist

#
# high level APIs with a global DistributionDirMap instance loaded
# on sys.path
#
_dist_dirs = DistributionDirMap()
_dist_dirs.load(*sys.path)

def get_distributions():
    """Provides an iterator that returns Distribution instances.

    Looks for `.egg-info` directories in `sys.path` and returns Distribution
    instances for each one of them.
    """
    return _dist_dirs.get_distributions()

def get_distribution(name):
    """Returns a ``Distribution`` instance for ``name``.

    Scans all elements in `sys.path` and looks for all directories ending
    with `.egg-info`. Returns a ``Distribution`` instance corresponding to
    the `.egg-info` directory that contains a `PKG-INFO` that matches
    ``name`` for the ``name`` metadata.

    Notice that there should be at most one result. The first result
    founded will be returned. If the directory is not found, returns ``None``.
    """
    return _dist_dirs.get_distribution(name)

def get_file_users(path):
    """Iterates over all distributions to find out which distribution uses
    ``path``.

    ``path`` can be a local absolute path or a relative '/'-separated path.
    """
    return _dist_dirs.get_file_users(path)


