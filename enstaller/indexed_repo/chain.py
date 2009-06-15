import os
import bz2
import string
import sys
import zipfile
from collections import defaultdict
from os.path import basename, join, isfile, isdir

import metadata
import utils
from requirement import Req, add_Reqs_to_spec, dist_as_req



def init():
    global verbose, local, repos, index

    verbose = False

    # Path to the local repository, must be set, if functions accessing the
    # local repository (see below) are called.
    local = None

    # Chain of repository, either local or remote, from which distributions
    # may be fetched, the local directory is always first.
    repos = ['local:/']

    # maps distributions to specs
    index = {}


def add_repo(repo, index_fn='index-depend.bz2'):
    """
    Add a repo to the chain, i.e. read the index file of the url,
    parse it and update the index.
    """
    if verbose:
        print "Adding repository:", repo
    assert repo.endswith('/'), repo

    data = utils.get_data_from_url(repo + index_fn, verbose=False)

    if index_fn.endswith('.bz2'):
        data = bz2.decompress(data)

    new_index = metadata.parse_depend_index(data)
    for spec in new_index.itervalues():
        add_Reqs_to_spec(spec)

    repos.append(repo)

    for distname, spec in new_index.iteritems():
        index[repo + distname] = spec


def get_matches_repo(req, repo):
    """
    Return the set of distributions which match the requirement from a
    specified repository.
    """
    matches = set()
    for dist, spec in index.iteritems():
        if utils.repo_dist(dist) == repo and req.matches(spec):
            matches.add(dist)
    return matches


def get_matches(req):
    """
    Return the set of distributions which match the requirement from the
    first repository in the chain which contains at least one match.
    """
    for repo in repos:
        matches = get_matches_repo(req, repo)
        if matches:
            return matches
    # no matching distributions are found in any repo
    return set()


def get_dist(req):
    """
    Return the distributions with the largest version and build number
    from the first repository which contains any matches.
    """
    matches = get_matches(req)
    if not matches:
        # no matching distributions were found in any repo
        print 'Error: No distribution found for requirement:', req
        sys.exit(1)
    # found matches, return the one with largest (version, build)
    lst = list(matches)
    lst.sort(key=utils.get_version_build)
    return lst[-1]


def reqs_dist(dist):
    """
    Return the set of requirement objects of the distribution.
    """
    if dist not in index:
        raise Exception("Index does not contain distribution: %r" % dist)
    return index[dist]['Reqs']


def get_reqs(req):
    """
    Returns the set of requirements, which are necessary to install 'req'.
    For each required (project) name, only one requirement, i.e. the one
    with the highest strictness, is contained in the output.
    """
    def _add_reqs(reqs, req):
        for dist in get_matches(req):
            for r in reqs_dist(dist):
                if r in reqs:
                    # a loop in the dependency tree will cause infinite
                    # recursion, unless we skip here.
                    continue
                reqs.add(r)
                # recursion
                _add_reqs(reqs, r)

    # first, get the set of all requirements
    reqs = set()
    _add_reqs(reqs, req)
    reqs.add(req)

    # the set of all required (project) names
    names = set(r.name for r in reqs)

    res = set()
    for name in names:
        # get all requirements for the name
        rs = [r for r in reqs if r.name == name]
        rs.sort(key=lambda r: r.strictness)
        # add the requirement with greatest strictness
        res.add(rs[-1])
    return res


def install_order(req):
    """
    Return the list of distributions which need to be installed.
    The returned list is given in dependency order, i.e. the distributions
    can be installed in this order without any package being installed
    before its dependencies got installed.
    """
    # all requirements necessary for install
    reqs = get_reqs(req)
    # the corresponding distributions (sorted because the output of this
    # function is otherwise not deterministic)
    dists = sorted(get_dist(r) for r in reqs)
    # maps dist -> set of required (project) names
    rns = {}
    for dist in dists:
        rns[dist] = set(r.name for r in reqs_dist(dist))

    # As long as we have things missing, simply look for things which
    # can be added, i.e. all the requirements have been added already
    res = []
    names_inst = set()
    while len(res) < len(dists):
        n = len(res)
        for dist in dists:
            if dist in res:
                continue
            # see if all required packages were added already
            if all(bool(n in names_inst) for n in rns[dist]):
                res.append(dist)
                names_inst.add(dist_as_req(dist).name)
                assert len(names_inst) == len(res)
        if len(res) == n:
            # nothing was added
            print "WARNING: Loop in the dependency graph"
            break
    return res

# --------------- functions which access the local repo -----------------

def fetch_dist(dist, force=False):
    """
    Get a distribution, i.e. copy the distribution into the local repo.
    """
    if dist not in index:
        raise Exception("distribution not found: %r" % dist)

    assert isdir(local), local

    dst = join(local, utils.filename_dist(dist))
    if not force and isfile(dst):
        if verbose:
            print "Not forcing refetch, %r already exists" % dst
        return

    data = utils.get_data_from_url(dist,
                                   index[dist]['md5'],
                                   index[dist]['size'],
                                   verbose=verbose)
    if verbose:
        print "Copying: %r" % dist
        print "     to: %r" % dst
    fo = open(dst, 'wb')
    fo.write(data)
    fo.close()


def index_local_file(filename):
    """
    Add an unindexed distribution (which must already exist in the local
    repository) to the index (in memory).  Note that the index file on
    disk remains unchanged.
    """
    if verbose:
        print "Adding %r to index" % filename

    assert isdir(local), local

    if filename != basename(filename):
        raise Exception("base filename expected, got %r" % filename)

    arcname = 'EGG-INFO/spec/depend'
    z = zipfile.ZipFile(join(local, filename))
    if arcname not in z.namelist():
        z.close()
        raise Exception("arcname=%r does not exist in %r" %
                        (arcname, filename))

    spec = metadata.parse_data(z.read(arcname), index=False)
    z.close()
    add_Reqs_to_spec(spec)
    index['local:/' + filename] = spec


def index_all_local_files():
    """
    Add all distributions to the index, see index_local_file() above.
    Note that no index file is written to disk.
    """
    for fn in os.listdir(local):
        if not fn.endswith('.egg'):
            continue
        if not utils.is_valid_eggname(fn):
            print("WARNING: %r invalid egg_name" % join(local, fn))
        index_local_file(fn)


# ------------- testing

def test(assert_files_exist=False):
    """
    Test the content of the repo for consistency.
    """
    allreqs = defaultdict(int)

    for fn in sorted(index.keys(), key=string.lower):
        if verbose:
            print fn

        if assert_files_exist:
            dist_path = join(local, fn)
            assert isfile(dist_path), dist_path

        spec = index[fn]
        for r in spec['Reqs']:
            allreqs[r] += 1
            d = get_dist(r)
            if verbose:
                print '\t', r, '->', get_dist(r)
            assert isinstance(r.versions, list) and r.versions
            assert all(v == v.strip() for v in r.versions)
            assert d in index

        r = Req('%(name)s %(version)s' % spec)
        assert dist_as_req(fn, strictness=2) == r
        assert get_dist(r)
        if verbose:
            print

    if verbose:
        print 70 * '='
    print "Index has %i distributions" % len(index)
    print "The following distributions are not required anywhere:"
    for fn, spec in index.iteritems():
        if not any(r.matches(spec) for r in allreqs):
            print '\t%s' % fn
    print 'OK'
