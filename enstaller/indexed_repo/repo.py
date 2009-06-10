import bz2
import string
import sys
import zipfile
from collections import defaultdict
from os.path import basename, join, isfile

from utils import (get_data_from_url, canonical, get_version_build,
                   split_eggname, repo_dist, filename_dist)
from metadata import parse_depend_index, parse_data
from requirement import Req



def add_Reqs_to_spec(spec):
    """
    add the 'Reqs' key, which maps to a set of requirement objects,
    to a spec dictionary.
    """
    spec['Reqs'] = set(Req(s) for s in spec['packages'])


def dist_as_req(dist, strictness=3):
    """
    Return the distribution in terms of the a requirement object.
    That is: What requirement gives me the distribution?
    """
    assert strictness >= 1
    name, version, build = split_eggname(filename_dist(dist))
    req_string = name
    if strictness >= 2:
        req_string += ' %s' % version
    if strictness >= 3:
        req_string += '-%s' % build
    return Req(req_string)



class IndexedRepo(object):

    def __init__(self, verbose=False):
        self.verbose = verbose

        # Local directory
        self.local = '.'

        # chain of repos, either local or remote, from which distributions
        # may be fetched, the local directory is always first.
        self.chain = ['local:/']

        # maps distributions to specs
        self.index = {}

    def add_repo(self, repo, index_fn='index-depend.bz2'):
        """
        Add a repo to the chain, i.e. read the index file of the url,
        parse it and update the index.
        """
        if self.verbose:
            print "Adding repo:", repo
        assert repo.endswith('/'), repo

        data = get_data_from_url(repo + index_fn, verbose=False)

        if index_fn.endswith('.bz2'):
            data = bz2.decompress(data)

        new_index = parse_depend_index(data)
        for spec in new_index.itervalues():
            add_Reqs_to_spec(spec)

        self.chain.append(repo)

        for distname, spec in new_index.iteritems():
            self.index[repo + distname] = spec

    def fetch_dist(self, dist, force=False):
        """
        Get a distribution, i.e. copy the distribution into the local repo.
        """
        if dist not in self.index:
            raise Exception("distribution not found: %r" % dist)

        dst = join(self.local, filename_dist(dist))
        if not force and isfile(dst):
            if self.verbose:
                print "Not forcing refetch, %r already exists" % dst
            return

        data = get_data_from_url(dist,
                                 self.index[dist]['md5'],
                                 self.index[dist]['size'],
                                 verbose=self.verbose)
        if self.verbose:
            print "Copying: %r" % dist
            print "     to: %r" % dst
        fo = open(dst, 'wb')
        fo.write(data)
        fo.close()

    # --------------------------------------------------------------------

    def get_matches_repo(self, req, repo):
        """
        Return the set of distributions which match the requirement from a
        specified repository.
        """
        matches = set()
        for dist, spec in self.index.iteritems():
            if repo_dist(dist) == repo and req.matches(spec):
                matches.add(dist)
        return matches

    def get_matches(self, req):
        """
        Return the set of distributions which match the requirement from the
        first repository in the chain which contains at least one match.
        """
        for repo in self.chain:
            matches = self.get_matches_repo(req, repo)
            if matches:
                return matches
        # no matching distributions are found in any repo
        return set()

    def get_dist(self, req):
        """
        Return the distributions with the largest version and build number
        from the first repository which contains any matches.
        """
        matches = self.get_matches(req)
        if not matches:
            # no matching distributions were found in any repo
            print 'Error: No distribution found for requirement:', req
            sys.exit(1)
        # found matches, return the one with largest (version, build)
        lst = list(matches)
        lst.sort(key=get_version_build)
        return lst[-1]

    def reqs_dist(self, dist):
        """
        Return the set of requirement objects of the distribution.
        """
        if dist not in self.index:
            raise Exception("Index does not contain distribution: %r" % dist)
        return self.index[dist]['Reqs']

    def _add_reqs(self, reqs, req):
        for dist in self.get_matches(req):
            for r in self.reqs_dist(dist):
                if r in reqs:
                    # a loop in the dependency tree will cause infinite
                    # recursion, unless we skip here.
                    continue
                reqs.add(r)
                # recursion
                self._add_reqs(reqs, r)

    def get_reqs(self, req):
        """
        Returns the set of requirements, which are necessary to install 'req'.
        For each required (project) name, only one requirement, i.e. the one
        with the highest strictness, is contained in the output.
        """
        # first, get the set of all requirements
        reqs = set()
        self._add_reqs(reqs, req)
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

    def install_order(self, req):
        """
        Return the list of distributions which need to be installed.
        The returned list is given in dependency order, i.e. the distributions
        can be installed in this order without any package being installed
        before its dependencies got installed.
        """
        # all requirements necessary for install
        reqs = self.get_reqs(req)
        # the corresponding distributions (sorted because the output of this
        # function is otherwise not deterministic)
        dists = sorted(self.get_dist(r) for r in reqs)
        # maps dist -> set of required (project) names
        rns = {}
        for dist in dists:
            rns[dist] = set(r.name for r in self.reqs_dist(dist))

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

    def add_to_local(self, filename):
        """
        Add an unindexed distribution, which must already exist in the local
        repository, to the index (in memory).  Note that the index file on
        disk remains unchanged.
        """
        if self.verbose:
            print "Adding %r to index" % filename

        if filename != basename(filename):
            raise Exception("base filename expected, got %r" % filename)

        arcname = 'EGG-INFO/spec/depend'
        z = zipfile.ZipFile(join(self.local, filename))
        if arcname not in z.namelist():
            z.close()
            raise Exception("arcname=%r does not exist in %r" %
                            (arcname, filename))

        spec = parse_data(z.read(arcname), index=False)
        z.close()
        add_Reqs_to_spec(spec)
        self.index['local:/' + filename] = spec

    def test(self, assert_files_exist=False):
        """
        Test the content of the repo for consistency.
        """
        allreqs = defaultdict(int)

        for fn in sorted(self.index.keys(), key=string.lower):
            if self.verbose:
                print fn

            if assert_files_exist:
                dist_path = join(self.local, fn)
                assert isfile(dist_path), dist_path

            spec = self.index[fn]
            for r in spec['Reqs']:
                allreqs[r] += 1
                d = self.get_dist(r)
                if self.verbose:
                    print '\t', r, '->', self.get_dist(r)
                assert isinstance(r.versions, list) and r.versions
                assert all(v == v.strip() for v in r.versions)
                assert d in self.index

            r = Req('%(name)s %(version)s' % spec)
            assert dist_as_req(fn, strictness=2) == r
            assert self.get_dist(r)
            if self.verbose:
                print

        if self.verbose:
            print 70 * '='
        print "Index has %i distributions" % len(self.index)
        print "The following distributions are not required anywhere:"
        for fn, spec in self.index.iteritems():
            if not any(r.matches(spec) for r in allreqs):
                print '\t%s' % fn
        print 'OK'



def fetch(repo, req_string,
          verbose=False,
          no_deps=False,
          dry_run=False,
          local_dir='.',
          ):
    """
    Convenient wrapper function
    """
    ir = IndexedRepo(verbose=verbose)
    ir.local = local_dir
    ir.add_repo(repo)

    req = Req(req_string)
    if verbose:
        print "==================== %r ====================" % req

    if no_deps:
        dists = [ir.get_dist(req)]
    else:
        dists = ir.install_order(req)

    if verbose:
        for d in dists:
            print '\t', filename_dist(d)

    for dist in dists:
        filename = filename_dist(dist)
        if verbose:
            print 70 * '='
            print dist
        if isfile(join(ir.local, filename)):
            print '%-60s [already exists]' % filename
        else:
            print '%-60s    [downloading]' % filename
            if dry_run:
                continue
            ir.fetch_dist(dist)
