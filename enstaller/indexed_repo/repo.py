import sys
import os
import string
import zipfile
from collections import defaultdict
from os.path import abspath, basename, join, isfile

from utils import get_data_from_url, canonical, get_version_build
from metadata import parse_depend_index, parse_data
from requirement import Req



def add_Reqs(spec):
    """
    add the 'Reqs' key to a spec dictionary.
    """
    spec['Reqs'] = set(Req(s) for s in spec['packages'])



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

    def add_repo(self, repo):
        """
        Add a repo to the list of extra repos, i.e. read the index file of
        the url, parse it and update the index.
        """
        if self.verbose:
            print "Adding repo:", repo
        assert repo.endswith('/'), repo

        data = get_data_from_url(repo + 'index-depend.bz2', verbose=False)

        new_index = parse_depend_index(data)
        for spec in new_index.itervalues():
            add_Reqs(spec)

        self.chain.append(repo)

        for distname, spec in new_index.iteritems():
            self.index[repo + distname] = spec

    def get_matches_repo(self, req, repo):
        """
        Return the set of distributions which match the requirement from the
        repository.  That is, all distribution which match the requirement.
        """
        matches = set()
        for dist, spec in self.index.iteritems():
            if dist.startswith(repo) and req.matches(spec):
                assert dist not in matches
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
        return None

    def get_dist(self, req):
        """
        Return the distributions with the largest version and build number
        from the first repository which contains any matches.
        """
        matches = self.get_matches(req)
        if matches is None:
            print 'Warning: No distribution found for', req
            # no matching distributions were found in any repo
            return None
        # found matches, return the one with largest (version, build)
        lst = sorted(matches, key=get_version_build)
        return lst[-1]

    def fetch_dist(self, req):
        """
        Get a distribution, i.e. copy the distribution into the local
        repo, according to how the chain is resolved.
        """
        dist = self.get_dist(req)
        if dist is None:
            raise Exception("no distribution found for %r" % req)

        if dist.startswith('local:/'):
            if self.verbose:
                print "Nothing to do for:", dist
            return

        data = get_data_from_url(dist,
                                 self.index[dist]['md5'],
                                 self.index[dist]['size'],
                                 verbose=self.verbose)

        dst = join(self.local, basename(dist))
        if self.verbose:
            print "Copying %r to %r" % (dist, dst)
        fo = open(dst, 'wb')
        fo.write(data)
        fo.close()

    def reqs_dist(self, dist):
        """
        Return the requirement objects (as a sorted list) which are a
        required by the distribution.
        """
        if dist not in self.index:
            raise("Index does not contain distribution: %r" % dist)
        return sorted(self.index[dist]['Reqs'])

    def dist_as_req(self, dist, strict=False):
        """
        Return the distribution in terms of the a requirement object.
        That is: What requirement gives me the distribution?
        Which is different from the method reqs_dist above.
        """
        spec = self.index[dist]
        tmp = '%(name)s %(version)s' % spec
        if strict:
            tmp += '-%(build)i' % spec
        return Req(tmp)

    def append_deps(self, dists, dist):
        """
        Append distributions required by (the distribution) 'dist' to the list
        recursively.
        """
        # first we need to know what the requirements of 'dist' are, we sort
        # them to because we want the list of distributions to be
        # deterministic.
        for r in self.reqs_dist(dist):
            # This is the distribution we finally want to append
            d = self.get_dist(r)

            # if the distribution 'd' is already in the list, we have already
            # added it (and it's dependencies) earlier.
            if d in dists:
                continue

            # Append dependencies of the 'd', before 'd' itself.
            self.append_deps(dists, d)

            # Make sure we've only added dependencies and not 'd' itself, which
            # could happen if there a loop is the dependency tree.
            assert d not in dists

            # Append the distribution itself.
            dists.append(d)

    def install_order(self, req):
        """
        Return the list of distributions which need to be installed to meet
        the requirement.
        The returned list is given in dependency order, i.e. the distributions
        can be installed in this order without any package being installed
        before its dependencies got installed.
        """
        # This is the actual distribution we append at the end
        d = self.get_dist(req)

        # Start with no distributions and add all dependencies of the required
        # distribution first.
        dists = []
        self.append_deps(dists, d)

        # dists now has all dependencies, before adding the required
        # distribution itself, we make sure it is not listed already.
        assert d not in dists
        dists.append(d)

        return dists

    def add_to_local(self, filename):
        """
        Add an unindexed distribution, which must already exist in the local
        repository, to the index (in memory).  Note that the index file on
        disk remains untouched.
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
        add_Reqs(spec)
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
            assert self.dist_as_req(fn) == r
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
