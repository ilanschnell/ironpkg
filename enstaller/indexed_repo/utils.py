import sys
import re
import hashlib
import urlparse
import urllib2
from os.path import basename

from egginst.utils import human_bytes, rm_rf



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


def cleanup_repo(repo):
    """
    Make sure a given repo string, i.e. a string specifying a repository,
    is valid and return a cleaned up version of the string.
    """
    if repo.startswith('local:'):
        assert repo == 'local:'

    elif repo.startswith('http://'):
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
    else:
        raise Exception("Invalid repo string: %r" % repo)

    return repo



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



def md5_file(path):
    """
    Returns the md5sum of the file (located at `path`) as a hexadecimal
    string of length 32.
    """
    fi = open(path, 'rb')
    h = hashlib.new('md5')
    while True:
        chunk = fi.read(4096)
        if not chunk:
            break
        h.update(chunk)
    fi.close()
    return h.hexdigest()


def open_with_auth(url):
    """
    Open a urllib2 request, handling HTTP authentication
    """
    try:
        import custom_tools
    except ImportError:
        custom_tools = False

    scheme, netloc, path, params, query, frag = urlparse.urlparse(url)
    assert query == ''
    auth, host = urllib2.splituser(netloc)
    if (auth is None and
        custom_tools and
        hasattr(custom_tools, 'epd_baseurl') and
        url.startswith(custom_tools.epd_baseurl)
        ):
        tmp = ''.join(chr(ord(c) ^ (3 + i))
                      for i, c in enumerate(custom_tools.epd_auth[12:-12]))
        assert tmp.endswith('@')
        auth = tmp[:-1]
    # TODO: get query from config file
    # query = OpenID
    # Attempt the request
    if auth:
        coded_auth = "Basic " + urllib2.unquote(auth).encode('base64').strip()
        new_url = urlparse.urlunparse((scheme, host, path,
                                       params, query, frag))
        request = urllib2.Request(new_url)
        request.add_header("Authorization", coded_auth)
    else:
        request = urllib2.Request(url)
    request.add_header('User-Agent', 'Enstaller')
    return urllib2.urlopen(request)


def pprint_fn_action(fn, action):
    """
    Pretty print the distribution name (filename) and an action, the width
    of the output corresponds to the with of the progress bar used by the
    function below.
    """
    print "%-56s %20s" % (fn, '[%s]' % action)


def write_data_from_url(fo, url, md5=None, size=None):
    """
    Read data from the url and write to the file handle fo, which must be
    open for writing.  Optionally check the MD5.  When the size in bytes
    is provided, a progress bar is displayed using the download/copy.
    """
    if size:
        sys.stdout.write('%9s [' % human_bytes(size))
        sys.stdout.flush()
        n = cur = 0

    if url.startswith('file://'):
        path = url[7:]
        fi = open(path, 'rb')
    elif url.startswith('http://'):
        fi = open_with_auth(url)
    else:
        raise Exception("Invalid url: %r" % url)

    h = hashlib.new('md5')

    if size and size < 16384:
        buffsize = 1
    else:
        buffsize = 256

    while True:
        chunk = fi.read(buffsize)
        if not chunk:
            break
        fo.write(chunk)
        if md5:
            h.update(chunk)
        if not size:
            continue
        n += len(chunk)
        if float(n) / size * 64 >= cur:
            sys.stdout.write('.')
            sys.stdout.flush()
            cur += 1

    if size:
        sys.stdout.write(']\n')
        sys.stdout.flush()

    fi.close()

    if md5 and h.hexdigest() != md5:
        sys.stderr.write("FATAL ERROR: Data received from\n\n"
                         "    %s\n\n"
                         "is corrupted.  MD5 sums mismatch.\n" % url)
        fo.close()
        sys.exit(1)
