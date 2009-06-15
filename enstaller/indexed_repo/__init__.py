"""
This is the indexed_repo API
============================

This file contains higher level functions.

"""
import string
from os.path import join, isfile

from chain import Chain
from requirement import Req, dist_as_req
from metadata import spec_from_dist
from utils import filename_dist, canonical



def pprint_distname_action(fn, action):
    print "%-56s %20s" % (fn, '[%s]' % action)


def resolve(req_string, local=None, repos=[], recur=True, fetch=False,
            fetch_force=False, verbose=False):
    """
    Resolves a requirement in a chain of indexed repositories.  An optional
    local repository, which is not indexed, can be specified.  This local
    repository is always resolved first, and optionally distributions are
    fetched here.
    The Return value is the list of distributions, in the order by which
    they would have to be installed on a clean system.  Note that, since this
    list may include distributions from the local repository, which is always
    searched first, a second call to this function may return a different
    result, if the fetch option was used.

    req_string:
        The requirement as a string, e.g. 'numpy 1.3.0', to resolve
        in the repository chain.

    local:
        The directory path to a local repository, i.e. a directory with
        distributions.  Index files are not necessary in here.  The fetch
        option puts distributions here.

    repos:
        A list of (indexed) repositories (file:// or http://) in the order
        by which they are searched, note that the local repo is always
        searched first.  Each element in the list is simply the string to
        the repo root (which needs to end with '/').

    recur:
        By default, all dependencies are resolved recursively.  If set to
        False, only the requirement is resolved.

    fetch:
        Download (http://) of copy (file://) the resolved distributions into
        the local repository.

    fetch_force:
        allow force when fetching
    """
    req = Req(req_string)

    if verbose:
        print "req = %r" % req

    c = Chain(local, repos, verbose)
    if verbose:
        print "c.local = %r" % c.local
        print 'c.repos:'
        for url in c.repos:
            print '\turl = %r' % url

    if fetch_force:
        # When using force, remove all entries from the local repo.
        # Otherwise, the resolution will contain entries from the local repo.
        for dist in c.index.keys():
            if dist.startswith('local:'):
                del c.index[dist]

    # resolve the dependencies
    if recur:
        dists = c.install_order(req)
    else:
        dists = [c.get_dist(req)]

    if verbose:
        print "Distributions:"
        for d in dists:
            print '\t', d

    if not fetch:
        return dists

    for dist in dists:
        fn = filename_dist(dist)
        if verbose:
            print 70 * '='
            print dist
        if fetch_force or not isfile(join(c.local, fn)):
            action = ['copying', 'downloading'][dist.startswith('http://')]
            pprint_distname_action(fn, action)
            c.fetch_dist(dist, force=fetch_force)
        else:
            pprint_distname_action(fn, 'already exists')

    return dists


#print Chain(repos=['file:///Users/ilan/repo-test/eggs/MacOSX/10.4_x86/']).index


def pprint_repo(local=None, repos=[], start=""):
    """
    Pretty print the distributions available in a repo, i.e. a "virtual"
    repo made of a chain of (indexed) repos.

    start:
        print only items which start with this string (case insensitive).
    """
    c = Chain(local, repos)
    start = canonical(start)
    names = set(spec['name'] for spec in c.index.itervalues())

    for name in sorted(names, key=string.lower):
        r = Req(name)
        versions = set()
        for dist in c.get_matches(r):
            if str(dist_as_req(dist)).startswith(start):
                versions.add(c.index[dist]['version'])
        if versions:
            print "%-20s %s" % (name, ', '.join(sorted(versions)))
