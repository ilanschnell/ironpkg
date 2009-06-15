"""
This is the indexed_repo API
============================

This file contains wrapper functions for common tasks, which can be
invoked in a single function call, i.e. the user does not have to
worry about all the little details involved to set up the correct
objects.

"""
import string
from os.path import join, isfile

import chain
from repo import IndexedRepo # to be removed later
from requirement import Req, dist_as_req
from platforms import Platforms
from metadata import spec_from_dist
from utils import filename_dist



def pprint_distname_action(fn, action):
    print "%-56s %20s" % (fn, '[%s]' % action)


def resolve(req_string, local=None, repos=[], recur=True, fetch=False,
            verbose=False):
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
    """
    req = Req(req_string)

    if verbose:
        print "req = %r" % req

    chain.init()
    chain.verbose = verbose
    chain.local = local
    for url in repos:
        # These are indexed repos (either local or http)
        chain.add_repo(url)

    if verbose:
        print "chain.local = %r" % chain.local
        print 'repos:'
        for url in chain.repos:
            print '\turl = %r' % url

    # Add all distributions in the local repo to the index (without writing
    # any index files)
    chain.index_all_local_files()

    if recur:
        dists = chain.install_order(req)
    else:
        dists = [chain.get_dist(req)]

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
        if isfile(join(chain.local, fn)):
            pprint_distname_action(fn, 'already exists')
        else:
            action = ['copying', 'downloading'][dist.startswith('http://')]
            pprint_distname_action(fn, action)
            chain.fetch_dist(dist)

    return dists


def pprint_repo(repos=[], start=""):
    """
    Pretty print the distributions available in a repo, i.e. a "virtual"
    repo made of a chain of (indexed) repos.

    start:
        print only items which start with this string.
    """
    chain.init()
    for url in repos:
        # These are indexed repos (either local or http)
        chain.add_repo(url)

    names = set(spec['name'] for spec in chain.index.itervalues())
    for name in sorted(names, key=string.lower):
        r = Req(name)
        versions = set()
        for dist in chain.get_matches(r):
            if str(dist_as_req(dist)).startswith(start):
                versions.add(chain.index[dist]['version'])
        if versions:
            print "%-20s %s" % (name, ', '.join(sorted(versions)))
