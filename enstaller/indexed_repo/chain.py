import os
import bz2
import string
import sys
import zipfile
from collections import defaultdict
from os.path import basename, join, isfile, isdir

import metadata
import utils
from requirement import Req, add_Reqs_to_spec



class Chain(object):

    def __init__(self, local=None, repos=[], verbose=False):
        self.verbose = verbose

        # maps distributions to specs
        self.index = {}

        # Path to the local repository, must be set, if functions accessing
        # the local repository (see below) are called.
        self.local = local

        if local is not None:
            # Add all distributions in the local repo to the index (without
            # writing any index files)
            self.index_all_files('local:')

        # Chain of repository, either local or remote, from which
        # distributions may be fetched, the local directory is always first.
        self.repos = ['local:']
        for repo in repos:
            # These are indexed repos (either file://... or http://...)
            self.add_repo(repo)


    def add_repo(self, repo, index_fn='index-depend.bz2'):
        """
        Add a repo to the chain, i.e. read the index file of the url,
        parse it and update the index.
        """
        if self.verbose:
            print "Adding repository:", repo
        if not repo.endswith('/'):
            repo += '/'

        self.repos.append(repo)

        index_url = repo + index_fn

        if index_url.startswith('file://'):
            if isfile(index_url[7:]):
                # A local url with index file
                if self.verbose:
                    print "\tfound index", index_url
            else:
                # A local url without index file
                self.index_all_files(repo)
                return

        if self.verbose:
            print "\treading:", index_url
        index_data = utils.get_data_from_url(index_url, verbose=False)

        if index_fn.endswith('.bz2'):
            index_data = bz2.decompress(index_data)

        new_index = metadata.parse_depend_index(index_data)
        for spec in new_index.itervalues():
            add_Reqs_to_spec(spec)

        for distname, spec in new_index.iteritems():
            self.index[repo + distname] = spec


    def get_matches_repo(self, req, repo):
        """
        Return the set of distributions which match the requirement from a
        specified repository.
        """
        matches = set()
        for dist, spec in self.index.iteritems():
            if utils.repo_dist(dist) == repo and req.matches(spec):
                matches.add(dist)
        return matches


    def get_matches(self, req):
        """
        Return the set of distributions which match the requirement from the
        first repository in the chain which contains at least one match.
        """
        for repo in self.repos:
            matches = self.get_matches_repo(req, repo)
            if matches:
                return matches
        # no matching distributions are found in any repo
        return set()


    def get_version_build(self, dist):
        """
        Returns a tuple(version, build) for a distribution.  This method is
        used below for determining the distribution with the largest version
        and build number.
        """
        spec = self.index[dist]
        return spec['version'], spec['build']


    def get_dist(self, req):
        """
        Return the distributions with the largest version and build number
        from the first repository which contains any matches.
        """
        matches = self.get_matches(req)
        if not matches:
            # no matching distributions were found in any repo
            print 'Error: No distribution found for requirement:', req
            print 'Repositories searched:'
            for r in self.repos:
                print '\t%r' % r
            sys.exit(1)
        # found matches, return the one with largest (version, build)
        lst = list(matches)
        lst.sort(key=self.get_version_build)
        return lst[-1]


    def reqs_dist(self, dist):
        """
        Return the set of requirement objects of the distribution.
        """
        if dist not in self.index:
            raise Exception("Index does not contain distribution: %r" % dist)
        return self.index[dist]['Reqs']


    def get_reqs(self, req):
        """
        Returns the set of requirements, which are necessary to install 'req'.
        For each required (project) name, only one requirement, i.e. the one
        with the highest strictness, is contained in the output.
        """
        def _add_reqs(reqs, req):
            for dist in self.get_matches(req):
                for r in self.reqs_dist(dist):
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
                    names_inst.add(self.index[dist]['name'])
                    assert len(names_inst) == len(res)
            if len(res) == n:
                # nothing was added
                print "WARNING: Loop in the dependency graph"
                break
        return res

    # --------------- methods which access the local repo -----------------

    def fetch_dist(self, dist, force=False):
        """
        Get a distribution, i.e. copy or download the distribution into
        the local repo.
        """
        if dist not in self.index:
            raise Exception("distribution not found: %r" % dist)

        assert isdir(self.local), self.local

        dst = join(self.local, utils.filename_dist(dist))
        if not force and isfile(dst):
            if self.verbose:
                print "Not forcing refetch, %r already exists" % dst
            return

        if dist.startswith('http://'):
            md5 = self.index[dist]['md5']
            size = self.index[dist]['size']
        else:
            md5 = size = None

        data = utils.get_data_from_url(dist, md5, size,
                                       verbose=self.verbose)
        if self.verbose:
            print "Copying: %r" % dist
            print "     to: %r" % dst
        fo = open(dst, 'wb')
        fo.write(data)
        fo.close()

    def dirname_repo(self, repo):
        if repo == 'local:':
            return self.local
        else:
            assert repo.startswith('file://')
            return repo[7:].rstrip(r'\/')

    def index_file(self, filename, repo):
        """
        Add an unindexed distribution, which must already exist in the
        repository, (which is either the local repository or a repository
        of the filesystem) to the index (in memory).  Note that the index
        file on disk remains unchanged.
        """
        dist = repo + filename
        if self.verbose:
            print "Adding %r to index" % dist

        if filename != basename(filename):
            raise Exception("base filename expected, got %r" % filename)

        arcname = 'EGG-INFO/spec/depend'
        z = zipfile.ZipFile(join(self.dirname_repo(repo), filename))
        if arcname not in z.namelist():
            z.close()
            raise Exception("arcname=%r does not exist in %r" %
                            (arcname, filename))

        spec = metadata.parse_data(z.read(arcname), index=False)
        z.close()
        add_Reqs_to_spec(spec)
        self.index[dist] = spec


    def index_all_files(self, repo):
        """
        Add all distributions to the index, see index_file() above.
        Note that no index file is written to disk.
        """
        for fn in os.listdir(self.dirname_repo(repo)):
            if not fn.endswith('.egg'):
                continue
            if not utils.is_valid_eggname(fn):
                print("WARNING: %r invalid egg_name" % join(self.local, fn))
            self.index_file(fn, repo)

    # ------------- testing

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
