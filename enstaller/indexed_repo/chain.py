import os
import sys
import zipfile
from cStringIO import StringIO
from os.path import basename, getsize, isfile, isdir, join

import metadata
import dist_naming
from requirement import Req, add_Reqs_to_spec, filter_name, dist_as_req
from enstaller.utils import (comparable_version, md5_file,
                             rm_rf, write_data_from_url)
from egginst.utils import pprint_fn_action


class Chain(object):

    def __init__(self, repos=[], verbose=False):
        self.verbose = verbose

        # maps distributions to specs
        self.index = {}

        # Chain of repositories, either local or remote
        self.repos = []
        for repo in repos:
            # These are file:// (optionally indexed) or http:// (indexed)
            self.add_repo(repo)

        if self.verbose:
            self.print_repos()


    def print_repos(self):
        print 'Repositories:'
        for r in self.repos:
            print '\t%r' % r


    def add_repo(self, repo, index_fn='index-depend.txt'):
        """
        Add a repo to the chain, i.e. read the index file of the url,
        parse it and update the index.
        """
        if self.verbose:
            print "Adding repository:", repo

        repo = dist_naming.cleanup_reponame(repo)

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

        faux = StringIO()
        write_data_from_url(faux, index_url)
        index_data = faux.getvalue()
        faux.close()

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
            if dist_naming.repo_dist(dist) == repo and req.matches(spec):
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
        Returns a tuple(version, build) for a distribution, version is a
        RationalVersion object (see verlib).  This method is used below
        for determining the distribution with the largest version and build
        number.
        """
        return dist_naming.comparable_spec(self.index[dist])


    def get_dist(self, req):
        """
        Return the distributions with the largest version and build number
        from the first repository which contains any matches.
        """
        lst = list(self.get_matches(req))
        lst.sort(key=self.get_version_build)
        if not lst:
            return None
        return lst[-1]


    def reqs_dist(self, dist):
        """
        Return the set of requirement objects of the distribution.
        """
        return self.index[dist]['Reqs']


    def select_new_reqs(self, reqs, dist):
        """
        Selects new requirements, which are listed as dependencies in the
        distribution 'dist', and are not already in the requirements 'reqs',
        unless the distribution requires something more strict.
        """
        result = set()
        for r in self.reqs_dist(dist):
            # from all the reqs (we already have collected) filter the
            # ones with the same project name
            rs2 = filter_name(reqs, r.name)
            if rs2:
                # if there are requirements for an existing project name,
                # only add if it is more strict
                for r2 in rs2:
                    if r2.strictness > r.strictness:
                        result.add(r2)
            else:
                # otherwise, just add it, there is no requirement for this
                # project yet
                result.add(r)
        return result


    def add_reqs(self, reqs, req, level=1):
        """
        Finds requirements of 'req', recursively and adds them to 'reqs',
        which is a dictionary mapping requirements to a
        tuple(recursion level, distribution which requires the requirement)
        """
        for dist in self.get_matches(req):
            for r in self.select_new_reqs(reqs, dist):
                if r in reqs:
                    continue
                reqs[r] = (level, dist)
                self.add_reqs(reqs, r, level + 1)


    def get_reqs(self, req):
        """
        Returns a dictionary mapping all requirements found recursively
        to the distribution which requires it.
        """
        # the root requirement (in the argument) itself maps to recursion
        # level 0 and a non-existent distribution (because the required by
        # the argument of this function and not any other distribution)
        assert req.strictness == 3, req
        reqs1 = {req: (0, 'ROOT')}

        # add all requirements for the root requirement
        self.add_reqs(reqs1, req)

        if self.verbose:
            print "Requirements: (-level, strictness)"
            for r in sorted(reqs1):
                print '\t%-33r %3i %3i' % (r, -reqs1[r][0], r.strictness)

        reqs2 = {}
        for name in set(r.name for r in reqs1):
            # get all requirements for the name
            rs = []
            for r in filter_name(reqs1, name):
                # append a tuple with:
                #   * tuple(negative recursion level, strictness)
                #   * requirement itself
                #   * distribution requiring it
                rs.append(((-reqs1[r][0], r.strictness), r, reqs1[r][1]))

            rs.sort()
            r, d = rs[-1][1:]
            reqs2[r] = d

        return reqs2


    def install_order(self, req, recur=True):
        """
        Return the list of distributions which need to be installed.
        The returned list is given in dependency order, i.e. the
        distributions can be installed in this order without any package
        being installed before its dependencies got installed.
        """
        if self.verbose:
            print "Determining install order for %r" % req
        dist_required = self.get_dist(req)
        if dist_required is None:
            return None

        if not recur:
            return [dist_required]

        req = dist_as_req(dist_required)
        if self.verbose:
            print dist_required
            print "Requirement: %r" % req

        dists = []
        for r, d in self.get_reqs(req).iteritems():
            dist = self.get_dist(r)
            if dist:
                dists.append(dist)
                continue
            print 'ERROR: No distribution found for: %r' % r
            if d != 'ROOT':
                print '       required by: %s' % d
            sys.exit(1)

        # the distributions corresponding to the requirements must be sorted
        # because the output of this function is otherwise not deterministic
        dists.sort()

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
                    names_inst.add(self.index[dist]['cname'])
                    assert len(names_inst) == len(res)
            if len(res) == n:
                # nothing was added
                raise Exception("Loop in the dependency graph")
        return res


    def list_versions(self, name):
        """
        given the name of a package, retruns a sorted list of versions for
        package `name` found in any repo.
        """
        versions = set()

        req = Req(name)
        for spec in self.index.itervalues():
            if req.matches(spec):
                versions.add(spec['version'])

        return sorted(versions, key=comparable_version)


    def fetch_dist(self, dist, fetch_dir, force=False, check_md5=False,
                   dry_run=False):
        """
        Get a distribution, i.e. copy or download the distribution into
        fetch_dir.

        force:
            force download or copy

        check_md5:
            when determining if a file needs to be downloaded or copied,
            check it's MD5.  This is, of course, slower but more reliable
            then just checking the file-size (which always done first).
            Note:
              * This option has option has nothing to do with checking the
                MD5 of a download.  The md5 is always checked when files are
                downloaded (regardless of this option).
              * If force=True, this option is has no effect, because the file
                is forcefully downloaded, ignoring any existing file (as well
                as the MD5).
        """
        md5 = self.index[dist].get('md5', None)
        size = self.index[dist].get('size', None)

        fn = dist_naming.filename_dist(dist)
        dst = join(fetch_dir, fn)
        # if force is not used, see if (i) the file exists (ii) its size is
        # the expected (iii) optionally, make sure the md5 is the expected.
        if (not force and isfile(dst) and getsize(dst) == size and
                   (not check_md5 or md5_file(dst) == md5)):
            if self.verbose:
                print "Not forcing refetch, %r already exists" % dst
            return

        pprint_fn_action(fn,
                 ['copying', 'downloading'][dist.startswith('http://')])
        if dry_run:
            return

        if self.verbose:
            print "Copying: %r" % dist
            print "     to: %r" % dst

        fo = open(dst + '.part', 'wb')
        write_data_from_url(fo, dist, md5, size)
        fo.close()
        rm_rf(dst)
        os.rename(dst + '.part', dst)


    def dirname_repo(self, repo):
        if repo.startswith('file://'):
            return repo[7:].rstrip(r'\/')
        return None


    def index_file(self, filename, repo):
        """
        Add an unindexed distribution, which must already exist in a local
        repository to the index (in memory).  Note that the index file on
        disk remains unchanged.
        """
        assert filename == basename(filename), filename
        dist = repo + filename
        if self.verbose:
            print "Adding %r to index" % dist

        arcname = 'EGG-INFO/spec/depend'
        z = zipfile.ZipFile(join(self.dirname_repo(repo), filename))
        if arcname not in z.namelist():
            z.close()
            raise Exception("zipfile %r has no arcname=%r" %
                            (filename, arcname))

        spec = metadata.parse_data(z.read(arcname))
        z.close()
        add_Reqs_to_spec(spec)
        self.index[dist] = spec


    def index_all_files(self, repo):
        """
        Add all distributions to the index, see index_file() above.
        Note that no index file is written to disk.
        """
        dir_path = self.dirname_repo(repo)
        assert isdir(dir_path), dir_path
        for fn in os.listdir(dir_path):
            if not fn.endswith('.egg'):
                continue
            if not dist_naming.is_valid_eggname(fn):
                print "WARNING: ignoring invalid egg name:", join(dir_path, fn)
                continue
            self.index_file(fn, repo)
