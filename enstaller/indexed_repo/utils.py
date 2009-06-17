import sys
import re
import hashlib
from os.path import basename

from egginst.utils import human_bytes



DIST_PAT = re.compile(r'(local:|file://.*[\\/]|http://.+/)([^\\/]+)$')

def split_dist(dist):
    """
    splits a distribution, e.g. 'http://www.example.com/repo/foo.egg', into
    repo and filename ('http://www.example.com/repo/', 'foo.egg').

    A distribution string, usually named 'dist', is always repo + filename.
    That is, simply adding the two strings will give the dist.  The terms
    filename and distname are used interchangeably.  There are currently
    the three types of repos:

    local:
    ======

    A local repository is where distributions are downloaded or copied to.
    Index file are always ignored in this repo, i.e. when a chain is
    initalized, the distributions in the local repo are always added to the
    index by inspecting the actual files.
    It is ALWAYS the first repo in the chain, EVEN when it is not used,
    i.e. no acutal directory is defined for the repo.  The repo string is
    always 'local:'.

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

    local:
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



def canonical(s):
    """
    Return a canonical representations of a project name.  This is used
    for finding matches.
    """
    s = s.lower()
    s = s.replace('-', '_')
    if s == 'tables':
        s = 'pytables'
    return s


_old_version_pat = re.compile(r'(\S+?)(n\d+)$')
def split_old_version(version):
    """
    Return tuple(version, build) for an old 'n' version.
    """
    m = _old_version_pat.match(version)
    if m is None:
        return version, None
    return m.group(1), int(m.group(2)[1:])

def split_old_eggname(eggname):
    assert basename(eggname) == eggname and eggname.endswith('.egg')
    name, old_version = eggname[:-4].split('-')[:2]
    version, build = split_old_version(old_version)
    assert build is not None
    return name, version, build



egg_pat = re.compile(r'([^-]+)-([^-]+)-(\d+).egg$')

def is_valid_eggname(eggname):
    return egg_pat.match(eggname)

def split_eggname(eggname):
    m = egg_pat.match(eggname)
    assert m, eggname
    return m.group(1), m.group(2), int(m.group(3))

def get_version_build(dist):
    """
    Return the version and build number of a distribution, as a
    tuple(version, build), where version is a string and build is an integer.
    """
    if ':' in dist:
        eggname = filename_dist(dist)
    else:
        eggname = dist
    return split_eggname(eggname)[1:]



def download_data(url, size, verbose=True):
    """
    Downloads data from the url, returns the data as a string.
    """
    from setuptools.package_index import open_with_auth

    if verbose:
        print "downloading data from: %r" % url
    if size:
        sys.stdout.write('%9s [' % human_bytes(size))
        sys.stdout.flush()
        cur = 0

    handle = open_with_auth(url)
    data = []

    if size and size < 16384:
        buffsize = 1
    else:
        buffsize = 256

    while True:
        chunk = handle.read(buffsize)
        if not chunk:
            break
        data.append(chunk)
        if not size:
            continue
        rat = float(buffsize) * len(data) / size
        if rat * 64 >= cur:
            sys.stdout.write('.')
            sys.stdout.flush()
            cur += 1

    if size:
        sys.stdout.write(']\n')
        sys.stdout.flush()

    data = ''.join(data)
    handle.close()
    if verbose:
        print "downloaded %i bytes" % len(data)

    return data


def get_data_from_url(url, md5=None, size=None, verbose=True):
    """
    Get data from a url and check optionally check the MD5.
    """
    if url.startswith('file://'):
        index_path = url[7:]
        data = open(index_path).read()

    elif url.startswith('http://'):
        data = download_data(url, size, verbose)

    else:
        raise Exception("Not valid url: " + url)

    if md5 is not None and hashlib.md5(data).hexdigest() != md5:
        sys.stderr.write("FATAL ERROR: Data received from\n\n"
                         "    %s\n\n"
                         "is corrupted.  MD5 sums mismatch.\n" % url)
        sys.exit(1)

    return data
