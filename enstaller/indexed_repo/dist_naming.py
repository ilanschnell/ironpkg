import re
from os.path import isdir

from enstaller.utils import abs_expanduser, comparable_version


DIST_PAT = re.compile(r'(file://.*[\\/]|http://.+/)([^\\/]+)$')

def split_dist(dist):
    """
    splits a distribution, e.g. 'http://www.example.com/repo/foo.egg', into
    repo and filename ('http://www.example.com/repo/', 'foo.egg').

    A distribution string, usually named 'dist', is always repo + filename.
    That is, simply adding the two strings will give the dist.  The terms
    filename and distname are used interchangeably.  There are currently
    the three types of repos:

    file://
    =======

    This repository type refers to a directory on a local filesystem, and
    may or may not be indexed.  That is, when an index file is found it is
    used to add the repository to the index, otherwise (if no index file
    exists), the distributions are added to the index by inspecting the
    actual files.

    http://
    =======

    A remote repository, which must contain a compressed index file.


    Naming examples:
    ================

    Here are some valid repo names:

    file:///usr/local/repo/
    file://E:\eggs\
    http://www.enthought.com/repo/EPD/eggs/Windows/x86/
    http://username:password@www.enthought.com/repo/EPD/eggs/Windows/x86/

    Note that, since we always have dist = repo + filename, the file:// repo
    name has to end with a forward slash (backslash on Windows), and the
    http:// always ends with a forward slash.
    """
    m = DIST_PAT.match(dist)
    assert m is not None, dist
    repo, filename = m.group(1), m.group(2)
    return repo, filename


def repo_dist(dist):
    return split_dist(dist)[0]


def filename_dist(dist):
    return split_dist(dist)[1]


egg_pat = re.compile(r'([\w.]+)-([\w.]+)-(\d+)\.egg$')

def is_valid_eggname(eggname):
    return bool(egg_pat.match(eggname))

def split_eggname(eggname):
    m = egg_pat.match(eggname)
    assert m, eggname
    return m.group(1), m.group(2), int(m.group(3))


def cleanup_reponame(repo):
    """
    Make sure a given repo string, i.e. a string specifying a repository,
    is valid and return a cleaned up version of the string.
    """
    if repo.startswith('http://'):
        if not repo.endswith('/'):
            repo += '/'

    elif repo.startswith('file://'):
        dir_path = repo[7:]
        if dir_path.startswith('/'):
            # Unix filename
            if not repo.endswith('/'):
                repo += '/'
        else:
            # Windows filename
            if not repo.endswith('\\'):
                repo += '\\'

    elif isdir(abs_expanduser(repo)):
        return cleanup_reponame('file://' + abs_expanduser(repo))

    else:
        raise Exception("Invalid repo string: %r" % repo)

    return repo


def comparable_spec(spec):
    """
    Returns a tuple(version, build) for a distribution, version is a
    RationalVersion object.  The result may be used for as a sort key.
    """
    return comparable_version(spec['version']), spec['build']
